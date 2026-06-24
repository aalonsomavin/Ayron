import json
import re
from collections.abc import Callable

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from apps.agent.tools.chart import (
    pop_chart_display,
    prepare_chart_for_render,
    validate_chart_input,
)
from apps.agent.tools.document import pop_document_display
from apps.agent.tools.html_report import pop_html_report_display
from apps.agent.tools.spreadsheet import pop_spreadsheet_display
from apps.agent.tools.display import PLAN_TOOL_LABEL, get_tool_display
from apps.agent.tools.table import pop_table_display, prepare_table_for_render, validate_table_input
from apps.chat.models import AgentEvent, Conversation, Message

PLAN_TOOLS = {"write_todos"}
DISPLAY_TOOLS = {
    "show_data_table",
    "show_chart",
    "create_document",
    "update_document",
    "create_spreadsheet",
    "update_spreadsheet",
    "publish_html_artifact",
}
TABLE_DISPLAY_TOOL = "show_data_table"
CHART_DISPLAY_TOOL = "show_chart"
CHART_TYPE_PATTERN = re.compile(r'"chart_type"\s*:\s*"(bar|line|pie)"')
VALID_CHART_TYPES = frozenset({"bar", "line", "pie"})
CREATE_DOCUMENT_TOOL = "create_document"
UPDATE_DOCUMENT_TOOL = "update_document"
CREATE_SPREADSHEET_TOOL = "create_spreadsheet"
UPDATE_SPREADSHEET_TOOL = "update_spreadsheet"
PUBLISH_HTML_ARTIFACT_TOOL = "publish_html_artifact"
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


def parse_tool_output_status(output: str) -> dict:
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict) or parsed.get("ok") is not False:
        return {}
    error = str(parsed.get("error", "Tool failed"))
    if len(error) > OUTPUT_SUMMARY_MAX_LEN:
        error = error[: OUTPUT_SUMMARY_MAX_LEN - 3] + "..."
    return {"success": False, "error": error}


def merge_tool_output_status(payload: dict, output: str) -> dict:
    status = parse_tool_output_status(output)
    if status:
        payload.update(status)
    return payload


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
        self.pending_chart_displays: dict[str, dict] = {}
        self.tool_call_inputs: dict[str, dict] = {}
        self.tool_call_args_text: dict[str, str] = {}

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

    def _accumulate_tool_args(self, tool_call_id: str, args) -> str:
        if isinstance(args, dict):
            fragment = json.dumps(args)
        elif isinstance(args, str):
            fragment = args
        else:
            fragment = ""
        if fragment:
            self.tool_call_args_text[tool_call_id] = (
                self.tool_call_args_text.get(tool_call_id, "") + fragment
            )
        return self.tool_call_args_text.get(tool_call_id, "")

    def _resolve_chart_type_hint(
        self,
        tool_call_id: str,
        tool_input: dict,
        args_text: str = "",
    ) -> str | None:
        staged = self.pending_chart_displays.get(tool_call_id)
        if staged:
            chart_type = str(staged.get("chart_type", "")).strip().lower()
            if chart_type in VALID_CHART_TYPES:
                return chart_type

        chart_type = str(tool_input.get("chart_type", "")).strip().lower()
        if chart_type in VALID_CHART_TYPES:
            return chart_type

        match = CHART_TYPE_PATTERN.search(args_text or "")
        if match:
            return match.group(1)
        return None

    def _chart_tool_start_ready(
        self,
        tool_call_id: str,
        tool_input: dict,
        args_text: str = "",
    ) -> bool:
        return self._resolve_chart_type_hint(tool_call_id, tool_input, args_text) is not None

    def _maybe_emit_tool_start(
        self,
        name: str,
        tool_call_id: str,
        tool_input: dict,
        args_text: str = "",
    ) -> None:
        if tool_call_id in self.started_tool_calls:
            return

        self.started_tool_calls.add(tool_call_id)
        resolved_input = self.tool_call_inputs.get(tool_call_id, tool_input)
        self._emit_tool_start(name, resolved_input, tool_call_id, args_text)

    def _ensure_chart_tool_start(self, tool_call_id: str | None) -> None:
        if not tool_call_id or tool_call_id in self.started_tool_calls:
            return
        tool_input = self.tool_call_inputs.get(tool_call_id, {})
        args_text = self.tool_call_args_text.get(tool_call_id, "")
        if not self._chart_tool_start_ready(tool_call_id, tool_input, args_text):
            return
        self.started_tool_calls.add(tool_call_id)
        self._emit_tool_start(CHART_DISPLAY_TOOL, tool_input, tool_call_id, args_text)

    def _handle_tool_call_chunk(self, tool_chunk: dict) -> None:
        tool_call_id = tool_chunk.get("id")
        name = tool_chunk.get("name")
        if not tool_call_id or not name:
            return

        raw_args = tool_chunk.get("args")
        args_text = self._accumulate_tool_args(tool_call_id, raw_args)
        tool_input = self._record_tool_input(tool_call_id, parse_tool_input(raw_args))
        self._stage_display_tool(name, tool_input, tool_call_id)
        self._maybe_emit_tool_start(name, tool_call_id, tool_input, args_text)

    def _handle_complete_tool_call(self, tool_call: dict) -> None:
        tool_call_id = tool_call.get("id")
        name = tool_call.get("name")
        if not tool_call_id or not name:
            return

        raw_args = tool_call.get("args")
        args_text = self._accumulate_tool_args(tool_call_id, raw_args)
        tool_input = self._record_tool_input(tool_call_id, parse_tool_input(raw_args))
        self._stage_display_tool(name, tool_input, tool_call_id)
        self._maybe_emit_tool_start(name, tool_call_id, tool_input, args_text)

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
            payload=merge_tool_output_status(
                {
                    "tool": name,
                    "output_summary": summary,
                    "tool_call_id": tool_call_id,
                    **get_tool_display(name),
                },
                output,
            ),
            message=self.message,
        )

    def _handle_display_tool_result(self, name: str, output: str, tool_call_id: str | None) -> None:
        if name == TABLE_DISPLAY_TOOL:
            result = self._resolve_table_display_result(output, tool_call_id)
            if result.get("ok") and result.get("rows"):
                self.persist(
                    conversation=self.conversation,
                    event_type=AgentEvent.EventType.TABLE,
                    payload={
                        **prepare_table_for_render(result),
                        "tool_call_id": tool_call_id,
                    },
                    message=self.message,
                )
            output_summary = "Tabla mostrada" if result.get("ok") else "Error al mostrar tabla"
        elif name == CHART_DISPLAY_TOOL:
            self._ensure_chart_tool_start(tool_call_id)
            result = self._resolve_chart_display_result(output, tool_call_id)
            if result.get("ok") and result.get("labels"):
                self.persist(
                    conversation=self.conversation,
                    event_type=AgentEvent.EventType.CHART,
                    payload={
                        **prepare_chart_for_render(result),
                        "tool_call_id": tool_call_id,
                    },
                    message=self.message,
                )
            output_summary = "Gráfico mostrado" if result.get("ok") else "Error al mostrar gráfico"
        elif name in (
            CREATE_DOCUMENT_TOOL,
            UPDATE_DOCUMENT_TOOL,
            CREATE_SPREADSHEET_TOOL,
            UPDATE_SPREADSHEET_TOOL,
            PUBLISH_HTML_ARTIFACT_TOOL,
        ):
            result = self._resolve_file_display_result(output, tool_call_id)
            if result.get("file_id") and not result.get("skip_chat_event"):
                event_type = (
                    AgentEvent.EventType.FILE_UPDATED
                    if result.get("updated")
                    else AgentEvent.EventType.FILE_CREATED
                )
                self.persist(
                    conversation=self.conversation,
                    event_type=event_type,
                    payload=result,
                    message=self.message,
                )
            is_html = result.get("format") == "html" or result.get("ext") == "HTML"
            is_sheet = (
                result.get("format") == "xlsx"
                or result.get("ext") == "XLSX"
                or result.get("kind") == "sheet"
            )
            if is_html:
                output_summary = (
                    "Reporte actualizado"
                    if result.get("updated")
                    else "Reporte publicado"
                ) if result.get("file_id") else "Error al publicar reporte"
            elif is_sheet:
                output_summary = (
                    "Hoja de cálculo actualizada"
                    if result.get("updated")
                    else "Hoja de cálculo creada"
                ) if result.get("file_id") else "Error al generar hoja de cálculo"
            else:
                output_summary = (
                    "Documento actualizado"
                    if result.get("updated")
                    else "Documento creado"
                ) if result.get("file_id") else "Error al generar documento"
        else:
            return

        self.persist(
            conversation=self.conversation,
            event_type=AgentEvent.EventType.TOOL_END,
            payload=merge_tool_output_status(
                {
                    "tool": name,
                    "output_summary": output_summary,
                    "tool_call_id": tool_call_id,
                    **get_tool_display(name),
                },
                output,
            ),
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

    def _resolve_chart_display_result(
        self,
        output: str,
        tool_call_id: str | None,
    ) -> dict:
        registry_result = pop_chart_display(tool_call_id)
        if registry_result:
            return registry_result

        if tool_call_id and tool_call_id in self.pending_chart_displays:
            return self.pending_chart_displays.pop(tool_call_id)

        if tool_call_id and tool_call_id in self.tool_call_inputs:
            try:
                tool_input = self.tool_call_inputs.pop(tool_call_id)
                return validate_chart_input(
                    tool_input.get("chart_type", ""),
                    tool_input.get("labels", []),
                    tool_input.get("series", []),
                    tool_input.get("title", ""),
                    tool_input.get("caption", ""),
                    tool_input.get("value_format", "number"),
                    tool_input.get("currency_label", ""),
                )
            except ValueError:
                pass

        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return {"ok": False}
        if parsed.get("ok") and parsed.get("labels"):
            return parsed
        return {"ok": False}

    def _resolve_file_display_result(
        self,
        output: str,
        tool_call_id: str | None,
    ) -> dict:
        registry_result = (
            pop_document_display(tool_call_id)
            or pop_spreadsheet_display(tool_call_id)
            or pop_html_report_display(tool_call_id)
        )
        if registry_result:
            return registry_result

        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return {}
        if parsed.get("ok") and parsed.get("file_id"):
            file_id = parsed["file_id"]
            payload = {
                "file_id": file_id,
                "name": parsed.get("name", "Document"),
                "ext": "DOCX",
                "format": "docx",
                "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "meta": "Document",
                "version": parsed.get("version", 1),
                "download_url": f"/files/{file_id}/download/",
                "preview_url": f"/files/{file_id}/preview/",
                "updated": parsed.get("action") == "updated",
            }
            return payload
        return {}

    def _resolve_document_display_result(
        self,
        output: str,
        tool_call_id: str | None,
    ) -> dict:
        return self._resolve_file_display_result(output, tool_call_id)

    def _emit_tool_start(
        self,
        name: str,
        tool_input: dict,
        tool_call_id: str,
        args_text: str = "",
    ) -> None:
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

        payload = {
            "tool": name,
            "input": tool_input,
            "tool_call_id": tool_call_id,
            **get_tool_display(name, tool_input),
        }
        if name == CHART_DISPLAY_TOOL:
            chart_type = self._resolve_chart_type_hint(tool_call_id, tool_input, args_text)
            if chart_type:
                payload["chart_type"] = chart_type

        self.persist(
            conversation=self.conversation,
            event_type=AgentEvent.EventType.TOOL_START,
            payload=payload,
            message=self.message,
        )

    def _stage_display_tool(self, name: str, tool_input: dict, tool_call_id: str) -> None:
        if name == TABLE_DISPLAY_TOOL:
            self._stage_table_display(tool_input, tool_call_id)
        elif name == CHART_DISPLAY_TOOL:
            self._stage_chart_display(tool_input, tool_call_id)

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

    def _stage_chart_display(self, tool_input: dict, tool_call_id: str) -> None:
        try:
            payload = validate_chart_input(
                tool_input.get("chart_type", ""),
                tool_input.get("labels", []),
                tool_input.get("series", []),
                tool_input.get("title", ""),
                tool_input.get("caption", ""),
                tool_input.get("value_format", "number"),
                tool_input.get("currency_label", ""),
            )
        except ValueError:
            return
        self.pending_chart_displays[tool_call_id] = payload

    def _emit_token(self, content: str) -> None:
        self.content_parts.append(content)
        self.persist(
            conversation=self.conversation,
            event_type=AgentEvent.EventType.TOKEN,
            payload={"content": content},
            message=self.message,
        )
