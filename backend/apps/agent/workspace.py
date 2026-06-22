from typing import TYPE_CHECKING

from deepagents.backends.protocol import _resolve_backend
from deepagents.backends.utils import file_data_to_string

from apps.agent.context import get_agent_backend
from apps.agent.skills import WORKSPACE_ROOT

if TYPE_CHECKING:
    from langchain.tools import ToolRuntime

DRAFT_ARTIFACT_ID = "_draft"
ARTIFACTS_PREFIX = f"{WORKSPACE_ROOT}artifacts/"


def artifact_path(file_id: str) -> str:
    return f"{ARTIFACTS_PREFIX}{file_id}.html"


def draft_artifact_path() -> str:
    return artifact_path(DRAFT_ARTIFACT_ID)


def normalize_workspace_path(path: str) -> str:
    normalized = (path or "").strip()
    if not normalized:
        raise ValueError("path is required")
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if not normalized.startswith(WORKSPACE_ROOT):
        raise ValueError(f"path must be under {WORKSPACE_ROOT}")
    if ".." in normalized.split("/"):
        raise ValueError("path must not contain parent directory segments")
    return normalized


def resolve_agent_backend(runtime: "ToolRuntime | None" = None):
    backend = get_agent_backend()
    if runtime is not None:
        return _resolve_backend(backend, runtime)
    return backend


def read_workspace_file(backend, path: str) -> str:
    normalized = normalize_workspace_path(path)
    result = backend.read(normalized)
    if result.error:
        raise ValueError(result.error)
    if not result.file_data:
        return ""
    return file_data_to_string(result.file_data)


def _workspace_file_exists(backend, path: str) -> bool:
    result = backend.read(path)
    if result.error:
        return False
    return result.file_data is not None


def write_workspace_file(backend, path: str, content: str) -> None:
    normalized = normalize_workspace_path(path)
    if _workspace_file_exists(backend, normalized):
        existing = read_workspace_file(backend, normalized)
        if existing == content:
            return
        result = backend.edit(normalized, existing, content)
        if result.error:
            raise ValueError(result.error)
        return
    result = backend.write(normalized, content)
    if result.error:
        raise ValueError(result.error)


def validate_and_writeback(backend, path: str) -> dict:
    from apps.agent.tools.html_report import infer_html_kind
    from apps.agent.tools.html_sanitize import normalize_agent_html

    normalized_path = normalize_workspace_path(path)
    raw = read_workspace_file(backend, normalized_path)
    if not raw.strip():
        raise ValueError("workspace file is empty")

    raw_bytes = len(raw.encode("utf-8"))
    normalized = normalize_agent_html(raw)
    canonical = normalized["html"] if normalized["full_document"] else normalized["body_html"]
    write_workspace_file(backend, normalized_path, canonical)

    warnings: list[str] = []
    canonical_bytes = len(canonical.encode("utf-8"))
    if canonical_bytes < raw_bytes:
        warnings.append("content was reduced during sanitization")

    return {
        "ok": True,
        "path": normalized_path,
        "html_kind": infer_html_kind(normalized["body_html"]),
        "byte_size": canonical_bytes,
        "warnings": warnings,
    }


def sync_artifact_to_workspace(backend, file_id: str, html: str) -> str:
    path = artifact_path(file_id)
    write_workspace_file(backend, path, html)
    return path


def relocate_workspace_artifact(backend, source_path: str, file_id: str) -> str:
    source = normalize_workspace_path(source_path)
    target = artifact_path(file_id)
    if source == target:
        return target
    content = read_workspace_file(backend, source)
    write_workspace_file(backend, target, content)
    return target
