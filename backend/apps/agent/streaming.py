import json
from collections.abc import Callable

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from apps.agent.tools.display import PLAN_TOOL_LABEL, get_tool_display
from apps.agent.tools.table import pop_table_display, prepare_table_for_render, validate_table_input
from apps.chat.models import AgentEvent, Conversation, Message

PLAN_TOOLS = {"write_todos"}
DISPLAY_TOOLS = {"show_data_table"}
OUTPUT_SUMMARY_MAX_LEN = 500


def extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content) if content else ""


def parse_tool_input(args) -> dict:
    if isinstance(args, dict):
        return args
    if isinstance(args, str) and args.strip():
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {}
    return {}


def merge_tool_input(existing: dict, incoming: dict) -> dict:
    if not incoming or incoming.get("raw"):
        return existing
    if not existing:
        return dict(incoming)
    merged = dict(existing)
    for key, value in incoming.items():
        if value is not None:
            merged[key] = value
    return merged


class StreamEventHandler:
    def __init__(
        self,
        conversation: Conversation,
        message: Message,
        persist_fn: Callable[..., tuple[int, AgentEvent]],
    ):
        self.conversation = conversation
        self.message = message
        self.persist = persist_fn
        self.content_parts: list[str] = []
        self.started_tool_calls: set[str] = set()
        self.completed_tool_calls: set[str] = set()
        self.pending_table_displays: dict[str, dict] = {}
        self.tool_call_inputs: dict[str, dict] = {}

    def get_content(self) -> str:
        return "".join(self.content_parts)

    def handle_chunk(self, chunk: dict) -> None:
        if chunk.get("type") != "messages":
            return
        if chunk.get("ns"):
            return

        token, _metadata = chunk["data"]
        tool_call_chunks = getattr(token, "tool_call_chunks", None) or []
        for tool_chunk in tool_call_chunks:
            self._handle_tool_call_chunk(tool_chunk)

        if isinstance(token, ToolMessage):
            self._handle_tool_result(token)
            return

        if isinstance(token, (AIMessage, AIMessageChunk)):
            for tool_call in getattr(token, "tool_calls", None) or []:
                self._handle_complete_tool_call(tool_call)

            content = extract_text_content(getattr(token, "content", ""))
            if content and not tool_call_chunks:
                self._emit_token(content)

    def _handle_tool_call_chunk(self, tool_chunk: dict) -> None:
        tool_call_id = tool_chunk.get("id")
        name = tool_chunk.get("name")
        if not tool_call_id or not name:
            return

        tool_input = self._record_tool_input(tool_call_id, parse_tool_input(tool_chunk.get("args")))
        if name == "show_data_table":
            self._stage_table_display(tool_input, tool_call_id)

        if tool_call_id in self.started_tool_calls:
            return

        self.started_tool_calls.add(tool_call_id)
        self._emit_tool_start(name, tool_input, tool_call_id)

    def _handle_complete_tool_call(self, tool_call: dict) -> None:
        tool_call_id = tool_call.get("id")
        name = tool_call.get("name")
        if not tool_call_id or not name:
            return

        tool_input = self._record_tool_input(tool_call_id, parse_tool_input(tool_call.get("args")))
        if name == "show_data_table":
            self._stage_table_display(tool_input, tool_call_id)

        if tool_call_id in self.started_tool_calls:
            return

        self.started_tool_calls.add(tool_call_id)
        self._emit_tool_start(name, tool_input, tool_call_id)

    def _record_tool_input(self, tool_call_id: str, tool_input: dict) -> dict:
        if tool_input:
            accumulated = merge_tool_input(
                self.tool_call_inputs.get(tool_call_id, {}),
                tool_input,
            )
            if accumulated:
                self.tool_call_inputs[tool_call_id] = accumulated
                return accumulated
        return self.tool_call_inputs.get(tool_call_id, tool_input)

    def _handle_tool_result(self, token) -> None:
        tool_call_id = getattr(token, "tool_call_id", None) or getattr(token, "id", None)
        dedupe_key = tool_call_id or getattr(token, "name", "")
        if not dedupe_key or dedupe_key in self.completed_tool_calls:
            return

        self.completed_tool_calls.add(dedupe_key)
        name = getattr(token, "name", "")
        if name in PLAN_TOOLS:
            return

        output = extract_text_content(getattr(token, "content", ""))
        if name in DISPLAY_TOOLS:
            self._handle_display_tool_result(name, output, tool_call_id)
            return

        summary = output[:OUTPUT_SUMMARY_MAX_LEN]
        if len(output) > OUTPUT_SUMMARY_MAX_LEN:
            summary += "..."

        self.persist(
            conversation=self.conversation,
            event_type=AgentEvent.EventType.TOOL_END,
            payload={
                "tool": name,
                "output_summary": summary,
                "tool_call_id": tool_call_id,
                **get_tool_display(name),
            },
            message=self.message,
        )

    def _handle_display_tool_result(self, name: str, output: str, tool_call_id: str | None) -> None:
        result = self._resolve_table_display_result(output, tool_call_id)

        if result.get("ok") and result.get("rows"):
            self.persist(
                conversation=self.conversation,
                event_type=AgentEvent.EventType.TABLE,
                payload=prepare_table_for_render(result),
                message=self.message,
            )

        self.persist(
            conversation=self.conversation,
            event_type=AgentEvent.EventType.TOOL_END,
            payload={
                "tool": name,
                "output_summary": "Tabla mostrada" if result.get("ok") else "Error al mostrar tabla",
                "tool_call_id": tool_call_id,
                **get_tool_display(name),
            },
            message=self.message,
        )

    def _resolve_table_display_result(
        self,
        output: str,
        tool_call_id: str | None,
    ) -> dict:
        registry_result = pop_table_display(tool_call_id)
        if registry_result:
            return registry_result

        if tool_call_id and tool_call_id in self.pending_table_displays:
            return self.pending_table_displays.pop(tool_call_id)

        if tool_call_id and tool_call_id in self.tool_call_inputs:
            try:
                tool_input = self.tool_call_inputs.pop(tool_call_id)
                return validate_table_input(
                    tool_input.get("columns", []),
                    tool_input.get("rows", []),
                    tool_input.get("caption", ""),
                    tool_input.get("column_widths"),
                )
            except ValueError:
                pass

        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return {"ok": False}
        if parsed.get("ok") and parsed.get("rows"):
            return parsed
        return {"ok": False}

    def _emit_tool_start(self, name: str, tool_input: dict, tool_call_id: str) -> None:
        if name in PLAN_TOOLS:
            todos = tool_input.get("todos", tool_input)
            self.persist(
                conversation=self.conversation,
                event_type=AgentEvent.EventType.PLAN,
                payload={
                    "todos": todos,
                    "tool_call_id": tool_call_id,
                    "tool": "write_todos",
                    "tool_label": PLAN_TOOL_LABEL,
                },
                message=self.message,
            )
            return

        self.persist(
            conversation=self.conversation,
            event_type=AgentEvent.EventType.TOOL_START,
            payload={
                "tool": name,
                "input": tool_input,
                "tool_call_id": tool_call_id,
                **get_tool_display(name, tool_input),
            },
            message=self.message,
        )
        if name == "show_data_table":
            self._stage_table_display(tool_input, tool_call_id)

    def _stage_table_display(self, tool_input: dict, tool_call_id: str) -> None:
        try:
            payload = validate_table_input(
                tool_input.get("columns", []),
                tool_input.get("rows", []),
                tool_input.get("caption", ""),
                tool_input.get("column_widths"),
            )
        except ValueError:
            return
        self.pending_table_displays[tool_call_id] = payload

    def _emit_token(self, content: str) -> None:
        self.content_parts.append(content)
        self.persist(
            conversation=self.conversation,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": content},
            message=self.message,
        )
