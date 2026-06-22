import pytest

from apps.agent.context import set_agent_backend
from apps.agent.tests.dict_workspace_backend import DictWorkspaceBackend
from apps.agent.tools.html_sanitize import sanitize_html_report
from apps.agent.workspace import (
    artifact_path,
    draft_artifact_path,
    normalize_workspace_path,
    read_workspace_file,
    relocate_workspace_artifact,
    validate_and_writeback,
    write_workspace_file,
)


class TestWorkspacePaths:
    def test_artifact_path(self):
        assert artifact_path("abc-123") == "/workspace/artifacts/abc-123.html"

    def test_draft_artifact_path(self):
        assert draft_artifact_path() == "/workspace/artifacts/_draft.html"

    def test_normalize_workspace_path_requires_workspace_root(self):
        with pytest.raises(ValueError, match="under /workspace/"):
            normalize_workspace_path("/skills/foo.html")

    def test_normalize_workspace_path_adds_leading_slash(self):
        assert normalize_workspace_path("workspace/artifacts/x.html") == (
            "/workspace/artifacts/x.html"
        )


class TestWorkspaceFileIO:
    @pytest.fixture
    def backend(self):
        backend = DictWorkspaceBackend()
        set_agent_backend(backend)
        return backend

    def test_write_and_read_roundtrip(self, backend):
        path = draft_artifact_path()
        write_workspace_file(backend, path, "<p>hello</p>")
        assert read_workspace_file(backend, path) == "<p>hello</p>"

    def test_write_workspace_file_updates_existing_path(self, backend):
        path = draft_artifact_path()
        write_workspace_file(backend, path, "<p>v1</p>")
        write_workspace_file(backend, path, "<p>v2</p>")
        assert read_workspace_file(backend, path) == "<p>v2</p>"

    def test_validate_and_writeback_over_existing_file(self):
        backend = DictWorkspaceBackend(reject_overwrite_on_write=True)
        set_agent_backend(backend)
        path = draft_artifact_path()
        backend.write(path, '<div class="ay-dash-page"><p>draft</p></div>')
        result = validate_and_writeback(backend, path)
        assert result["ok"] is True
        assert "ay-dash-page" in read_workspace_file(backend, path)

    def test_validate_and_writeback_strips_script_tags(self, backend):
        path = draft_artifact_path()
        raw = '<div class="ay-dash-page"><script>alert(1)</script><p>ok</p></div>'
        write_workspace_file(backend, path, raw)
        result = validate_and_writeback(backend, path)
        assert result["ok"] is True
        cleaned = read_workspace_file(backend, path)
        assert "alert" not in cleaned
        assert "ay-dash-page" in cleaned
        assert result["html_kind"] == "dashboard"

    def test_relocate_workspace_artifact(self, backend):
        source = draft_artifact_path()
        write_workspace_file(backend, source, "<p>draft</p>")
        target = relocate_workspace_artifact(backend, source, "file-1")
        assert target == artifact_path("file-1")
        assert read_workspace_file(backend, target) == "<p>draft</p>"


class TestSanitizeIntegration:
    def test_json_script_preserved(self):
        html = """
        <div class="ay-chart">
          <script type="application/json">{"chart_type":"bar","labels":["A"],"datasets":[]}</script>
        </div>
        """
        cleaned = sanitize_html_report(html)
        assert "application/json" in cleaned
