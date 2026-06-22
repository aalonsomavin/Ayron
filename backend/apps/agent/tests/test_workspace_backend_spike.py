import json

import pytest
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import MemorySaver

from apps.agent.context import set_agent_backend
from apps.agent.skills import (
    PLATFORM_SKILLS_PATH,
    WORKSPACE_ROOT,
    build_agent_backend,
    get_platform_skill_permissions,
    get_platform_skill_sources,
    get_platform_skills_dir,
)
from apps.agent.workspace import read_workspace_file, resolve_agent_backend, write_workspace_file
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.utils import file_data_to_string


class ToolCallingFakeChatModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.i >= len(self.responses):
            response = AIMessage(content="done")
        else:
            response = self.responses[self.i]
            self.i += 1
        return ChatResult(generations=[ChatGeneration(message=response)])


@tool
def _spike_workspace_write(path: str, content: str, runtime: ToolRuntime) -> str:
    """Write a file to the agent workspace for spike testing."""
    backend = resolve_agent_backend(runtime)
    write_workspace_file(backend, path, content)
    return json.dumps({"ok": True, "path": path})


@tool
def _spike_workspace_read(path: str, runtime: ToolRuntime) -> str:
    """Read a file from the agent workspace for spike testing."""
    backend = resolve_agent_backend(runtime)
    content = read_workspace_file(backend, path)
    return json.dumps({"ok": True, "path": path, "content": content})


@pytest.mark.django_db
class TestCompositeBackendSpike:
    def test_build_agent_backend_routes(self):
        backend = build_agent_backend()
        assert isinstance(backend, CompositeBackend)
        assert isinstance(backend.default, StateBackend)
        assert PLATFORM_SKILLS_PATH in backend.routes
        assert isinstance(backend.routes[PLATFORM_SKILLS_PATH], FilesystemBackend)
        assert backend.artifacts_root == WORKSPACE_ROOT

    def test_skills_path_reads_from_disk(self):
        backend = build_agent_backend()
        skill_path = f"{PLATFORM_SKILLS_PATH}html-reports/SKILL.md"
        result = backend.read(skill_path)
        assert result.error is None
        assert "publish_html_artifact" in file_data_to_string(result.file_data or {})

    def test_platform_skill_permissions_deny_skills_writes(self):
        rules = get_platform_skill_permissions()
        assert len(rules) == 1
        assert rules[0].mode == "deny"
        assert rules[0].operations == ["write"]
        assert rules[0].paths == [f"{PLATFORM_SKILLS_PATH}**"]

    def test_custom_tool_reads_and_writes_workspace_via_tool_runtime(self):
        backend = build_agent_backend()
        set_agent_backend(backend)

        write_call = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "_spike_workspace_write",
                    "args": {
                        "path": f"{WORKSPACE_ROOT}test.html",
                        "content": "<p>workspace spike</p>",
                    },
                    "id": "call-write",
                    "type": "tool_call",
                }
            ],
        )
        read_call = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "_spike_workspace_read",
                    "args": {"path": f"{WORKSPACE_ROOT}test.html"},
                    "id": "call-read",
                    "type": "tool_call",
                }
            ],
        )
        done = AIMessage(content="done")

        model = ToolCallingFakeChatModel(responses=[write_call, read_call, done])
        agent = create_deep_agent(
            model=model,
            tools=[_spike_workspace_write, _spike_workspace_read],
            backend=backend,
            skills=get_platform_skill_sources(),
            permissions=get_platform_skill_permissions(),
            checkpointer=MemorySaver(),
        )
        config = {"configurable": {"thread_id": "workspace-spike-thread"}}

        agent.invoke({"messages": [{"role": "user", "content": "write workspace file"}]}, config=config)
        result = agent.invoke(
            {"messages": [{"role": "user", "content": "read workspace file"}]},
            config=config,
        )

        tool_messages = [
            message
            for message in result["messages"]
            if getattr(message, "type", None) == "tool" or message.__class__.__name__ == "ToolMessage"
        ]
        read_payload = json.loads(tool_messages[-1].content)
        assert read_payload["ok"] is True
        assert read_payload["content"] == "<p>workspace spike</p>"

    def test_workspace_file_survives_checkpoint_between_turns(self):
        backend = build_agent_backend()
        set_agent_backend(backend)

        write_call = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "_spike_workspace_write",
                    "args": {
                        "path": f"{WORKSPACE_ROOT}artifacts/_draft.html",
                        "content": "<p>checkpointed draft</p>",
                    },
                    "id": "call-write",
                    "type": "tool_call",
                }
            ],
        )
        read_call = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "_spike_workspace_read",
                    "args": {"path": f"{WORKSPACE_ROOT}artifacts/_draft.html"},
                    "id": "call-read",
                    "type": "tool_call",
                }
            ],
        )
        done = AIMessage(content="done")

        model = ToolCallingFakeChatModel(responses=[write_call, done, read_call, done])
        agent = create_deep_agent(
            model=model,
            tools=[_spike_workspace_write, _spike_workspace_read],
            backend=backend,
            skills=get_platform_skill_sources(),
            permissions=get_platform_skill_permissions(),
            checkpointer=MemorySaver(),
        )
        config = {"configurable": {"thread_id": "workspace-checkpoint-thread"}}

        agent.invoke({"messages": [{"role": "user", "content": "write draft"}]}, config=config)
        result = agent.invoke({"messages": [{"role": "user", "content": "read draft"}]}, config=config)

        state = agent.get_state(config)
        files = state.values.get("files") or {}
        assert f"{WORKSPACE_ROOT}artifacts/_draft.html" in files

        tool_messages = [
            message
            for message in result["messages"]
            if getattr(message, "type", None) == "tool" or message.__class__.__name__ == "ToolMessage"
        ]
        read_payload = json.loads(tool_messages[-1].content)
        assert read_payload["content"] == "<p>checkpointed draft</p>"

    def test_starter_dashboard_readable_from_skills_route(self):
        backend = build_agent_backend()
        starter_path = f"{PLATFORM_SKILLS_PATH}html-reports/starter-dashboard.html"
        result = backend.read(starter_path)
        assert result.error is None
        assert "ay-dash" in file_data_to_string(result.file_data or {})
        assert (get_platform_skills_dir() / "html-reports" / "starter-dashboard.html").is_file()
