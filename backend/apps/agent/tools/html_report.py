import json
import re
from datetime import date
from pathlib import Path
from typing import Annotated

from django.conf import settings
from langchain.tools import ToolRuntime
from langchain_core.tools import InjectedToolCallId, tool

from apps.agent.cancellation import check_agent_not_cancelled
from apps.agent.context import get_agent_conversation, get_agent_user
from apps.agent.workspace import (
    read_workspace_file,
    relocate_workspace_artifact,
    resolve_agent_backend,
    sync_artifact_to_workspace,
    validate_and_writeback,
    write_workspace_file,
)
from apps.agent.tools.errors import build_tool_error_response
from apps.agent.tools.document_style import footer_attribution_text
from apps.agent.tools.html_insight import normalize_insight_markup
from apps.agent.tools.html_sanitize import normalize_agent_html
from apps.files.models import HTML_MIME
from apps.files.services import (
    context_update_error,
    escape_preview_text as esc,
    get_file_for_conversation,
    save_generated_file,
    serialize_file_for_ui,
    update_generated_file,
    _normalize_html_filename,
)

_HTML_REPORT_DISPLAY_REGISTRY: dict[str, dict] = {}

AGENT_INSTRUCTION_AFTER_HTML_REPORT = (
    "El reporte ya está visible en el chat del usuario. "
    "NO repitas el contenido del informe en tu siguiente mensaje. "
    "Solo añade una frase breve si aporta contexto, o termina sin texto."
)

HTML_KIND_REPORT = "report"
HTML_KIND_DASHBOARD = "dashboard"
HTML_KINDS = {HTML_KIND_REPORT, HTML_KIND_DASHBOARD}

STATUS_PUBLISHED = "published"


def pop_html_report_display(tool_call_id: str | None) -> dict | None:
    if not tool_call_id:
        return None
    return _HTML_REPORT_DISPLAY_REGISTRY.pop(tool_call_id, None)


def _sanitize_filename(name: str, fallback: str) -> str:
    return _normalize_html_filename(name, fallback)


def infer_html_kind(body_html: str) -> str:
    if "ay-dash-page" in body_html:
        return HTML_KIND_DASHBOARD
    return HTML_KIND_REPORT


def resolve_html_kind(body_html: str, html_kind: str | None = None) -> str:
    inferred = infer_html_kind(body_html)
    if html_kind is None or not str(html_kind).strip():
        return inferred
    normalized = str(html_kind).strip().lower()
    if normalized not in HTML_KINDS:
        raise ValueError(f"html_kind must be one of: {', '.join(sorted(HTML_KINDS))}")
    if normalized != inferred:
        raise ValueError(
            f"html_kind={normalized!r} does not match markup "
            f"(expected {inferred!r} for this HTML)"
        )
    return normalized


def validate_html_report_content(
    title: str,
    html: str,
    subtitle: str = "",
    html_kind: str | None = None,
    *,
    status: str | None = None,
) -> dict:
    if not title or not str(title).strip():
        raise ValueError("title is required")
    normalized = normalize_agent_html(html)
    body_html = normalized["body_html"]
    result = {
        "format": "html",
        "html_kind": resolve_html_kind(body_html, html_kind),
        "title": str(title).strip(),
        "subtitle": str(subtitle or "").strip(),
        "html": normalized["html"],
        "body_html": body_html,
        "full_document": normalized["full_document"],
        "status": status or STATUS_PUBLISHED,
    }
    return result


def _load_export_css() -> str:
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "html_report_export.css"
    return css_path.read_text(encoding="utf-8")


def _load_dashboard_css() -> str:
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "html_report_dashboard.css"
    return css_path.read_text(encoding="utf-8")


def _load_chart_css() -> str:
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "html_report_chart.css"
    return css_path.read_text(encoding="utf-8")


def _load_report_css(*, include_charts: bool = False) -> str:
    css = f"{_load_export_css()}\n{_load_dashboard_css()}"
    if include_charts:
        css = f"{css}\n{_load_chart_css()}"
    return css


def _body_has_charts(body_html: str) -> bool:
    return "ay-chart" in body_html or "chart.js" in body_html.lower()


def _report_font_links() -> str:
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
        "?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap\">"
    )


def _footer_html() -> str:
    return f'<footer class="ay-html-report__footer">{esc(footer_attribution_text(date.today()))}</footer>'


def _uses_report_shell(body_html: str) -> bool:
    return "ay-dash-page" in body_html or "ay-report-prose" in body_html


def _wrap_export_body(body_html: str) -> str:
    if _uses_report_shell(body_html):
        return f"{body_html}{_footer_html()}"
    return f'<div class="ay-html-report">{body_html}{_footer_html()}</div>'


def _preview_document_shell(body_html: str, *, title: str = "Preview") -> str:
    include_charts = _body_has_charts(body_html)
    return (
        "<!DOCTYPE html>"
        '<html lang="es">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title>"
        f"{_report_font_links()}"
        f"<style>{_load_report_css(include_charts=include_charts)}</style>"
        "</head>"
        "<body>"
        f'<div class="ay-html-report-preview">{body_html}</div>'
        "</body>"
        "</html>"
    )


def build_preview_html(content_json: dict) -> str:
    if content_json.get("full_document"):
        html = content_json.get("html") or ""
        if html.strip():
            return html

    body_html = content_json.get("body_html") or content_json.get("html") or ""
    body_html = normalize_insight_markup(body_html)
    title = content_json.get("title") or "Preview"
    return _preview_document_shell(body_html, title=title)


def build_preview_fragment(content_json: dict) -> str:
    return build_preview_html(content_json)


def build_export_html(content_json: dict) -> str:
    title = esc(content_json.get("title", "Reporte"))
    generated_on = esc(footer_attribution_text(date.today()))

    if content_json.get("full_document"):
        html = content_json.get("html") or ""
        if "ay-html-report__footer" not in html and generated_on not in html:
            if re.search(r"</body>", html, re.IGNORECASE):
                html = re.sub(
                    r"</body>",
                    f"{_footer_html()}</body>",
                    html,
                    count=1,
                    flags=re.IGNORECASE,
                )
            else:
                html = f"{html}{_footer_html()}"
        return html

    body_html = content_json.get("body_html") or content_json.get("html") or ""
    body_html = normalize_insight_markup(body_html)
    wrapped_body = _wrap_export_body(body_html)
    include_charts = _body_has_charts(body_html)
    return (
        "<!DOCTYPE html>"
        '<html lang="es">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title>"
        f"{_report_font_links()}"
        f"<style>{_load_report_css(include_charts=include_charts)}</style>"
        "</head>"
        "<body>"
        f"{wrapped_body}"
        "</body>"
        "</html>"
    )


def preview_html_for_file(content_json: dict | None, preview_html: str) -> str:
    if content_json and content_json.get("format") == "html":
        if content_json.get("body_html") or content_json.get("html"):
            return build_preview_html(content_json)
    return preview_html or ""


def _build_agent_tool_response(
    file_obj,
    action: str,
    *,
    agent_instruction: str | None = None,
    workspace_path: str | None = None,
) -> str:
    payload = {
        "ok": True,
        "action": action,
        "file_id": str(file_obj.id),
        "name": file_obj.original_name,
        "version": file_obj.version,
        "status": STATUS_PUBLISHED,
        "agent_instruction": agent_instruction or AGENT_INSTRUCTION_AFTER_HTML_REPORT,
    }
    if workspace_path:
        payload["workspace_path"] = workspace_path
    return json.dumps(payload)


def _register_display(
    tool_call_id: str,
    file_obj,
    *,
    updated: bool = False,
) -> None:
    payload = serialize_file_for_ui(file_obj)
    payload["updated"] = updated
    payload["status"] = STATUS_PUBLISHED
    _HTML_REPORT_DISPLAY_REGISTRY[tool_call_id] = payload


def _persist_html_file(
    *,
    conversation,
    user,
    content_json: dict,
    original_name: str,
    file_obj=None,
):
    export_html = build_export_html(content_json)
    preview_html = build_preview_html(content_json)
    if file_obj is None:
        return save_generated_file(
            conversation=conversation,
            user=user,
            original_name=original_name,
            content_json=content_json,
            file_bytes=export_html.encode("utf-8"),
            preview_html=preview_html,
            mime_type=HTML_MIME,
        )
    file_obj.original_name = original_name
    return update_generated_file(
        file_obj=file_obj,
        content_json=content_json,
        file_bytes=export_html.encode("utf-8"),
        preview_html=preview_html,
    )


def _content_json_from_workspace_html(
    html: str,
    title: str,
    subtitle: str = "",
    html_kind: str | None = None,
) -> dict:
    return validate_html_report_content(title, html, subtitle, html_kind=html_kind)


def run_hydrate_html_artifact(file_id: str, runtime: ToolRuntime | None = None) -> str:
    """Load a published HTML artifact into the agent workspace for editing.

    Writes the current markup to `/workspace/artifacts/{file_id}.html`. Use
    `read_file`, `grep`, or `edit_file` on that path, then `validate_html_artifact`
    and `publish_html_artifact` with the same `file_id`.
    """
    conversation = get_agent_conversation()
    if conversation is None:
        return build_tool_error_response("No conversation context")

    file_obj = get_file_for_conversation(file_id, conversation)
    if file_obj is None or file_obj.format_key != "html":
        return build_tool_error_response("HTML report not found in this conversation")

    body_html = file_obj.content_json.get("body_html") or file_obj.content_json.get("html", "")
    html = file_obj.content_json.get("html") or body_html
    try:
        backend = resolve_agent_backend(runtime)
        path = sync_artifact_to_workspace(backend, str(file_obj.id), html)
    except ValueError as exc:
        return build_tool_error_response(str(exc))

    return json.dumps(
        {
            "ok": True,
            "action": "hydrated",
            "file_id": str(file_obj.id),
            "path": path,
            "title": file_obj.content_json.get("title", ""),
            "subtitle": file_obj.content_json.get("subtitle", ""),
            "html_kind": file_obj.content_json.get("html_kind") or infer_html_kind(body_html),
            "agent_instruction": (
                "El artifact está en el workspace. Edítalo con las tools de filesystem, "
                "luego validate_html_artifact y publish_html_artifact."
            ),
        }
    )


@tool
def hydrate_html_artifact(file_id: str, runtime: ToolRuntime) -> str:
    """Load a published HTML artifact into the agent workspace for editing.

    Writes the current markup to `/workspace/artifacts/{file_id}.html`. Use
    `read_file`, `grep`, or `edit_file` on that path, then `validate_html_artifact`
    and `publish_html_artifact` with the same `file_id`.
    """
    return run_hydrate_html_artifact(file_id, runtime)


def run_validate_html_artifact(path: str, runtime: ToolRuntime | None = None) -> str:
    """Sanitize a workspace HTML file and write the canonical version back.

    Call after editing HTML in `/workspace/artifacts/`. Required before
    `publish_html_artifact`. Read `/skills/html-reports/GUIDELINES.md` before writing HTML.
    """
    check_agent_not_cancelled()
    try:
        backend = resolve_agent_backend(runtime)
        result = validate_and_writeback(backend, path)
    except ValueError as exc:
        return build_tool_error_response(str(exc))
    return json.dumps(result)


@tool
def validate_html_artifact(path: str, runtime: ToolRuntime) -> str:
    """Sanitize a workspace HTML file and write the canonical version back.

    Call after editing HTML in `/workspace/artifacts/`. Required before
    `publish_html_artifact`. Read `/skills/html-reports/GUIDELINES.md` before writing HTML.
    """
    return run_validate_html_artifact(path, runtime)


def run_publish_html_artifact(
    path: str,
    title: str,
    runtime: ToolRuntime | None = None,
    subtitle: str = "",
    filename: str = "",
    file_id: str = "",
    tool_call_id: str = "",
) -> str:
    """Publish a validated workspace HTML file to the user.

    The file at `path` must exist under `/workspace/` (e.g. `/workspace/artifacts/_draft.html`
    for new reports, or `/workspace/artifacts/{file_id}.html` after hydrate).

  For new artifacts, omit `file_id`. For updates, pass the existing `file_id`.
  Call `validate_html_artifact` on `path` before publishing.
    """
    check_agent_not_cancelled()
    conversation = get_agent_conversation()
    user = get_agent_user()
    if conversation is None or user is None:
        return build_tool_error_response("No conversation context")

    try:
        backend = resolve_agent_backend(runtime)
        source_path = path.strip()
        html = read_workspace_file(backend, source_path)
        normalized = normalize_agent_html(html)
        workspace_html = (
            normalized["html"] if normalized["full_document"] else normalized["body_html"]
        )
        write_workspace_file(backend, source_path, workspace_html)
    except ValueError as exc:
        return build_tool_error_response(str(exc))

    existing_file = None
    normalized_file_id = file_id.strip() if file_id else ""
    if normalized_file_id:
        existing_file = get_file_for_conversation(normalized_file_id, conversation)
        if existing_file is None or existing_file.format_key != "html":
            return build_tool_error_response("HTML report not found in this conversation")
        blocked = context_update_error(existing_file)
        if blocked:
            return build_tool_error_response(blocked)

    resolved_title = title.strip() if title else ""
    if not resolved_title:
        if existing_file:
            resolved_title = existing_file.content_json.get("title", "")
        else:
            return build_tool_error_response("title is required")

    resolved_subtitle = subtitle
    if not resolved_subtitle and existing_file:
        resolved_subtitle = existing_file.content_json.get("subtitle", "")

    try:
        content_json = _content_json_from_workspace_html(
            workspace_html,
            resolved_title,
            resolved_subtitle,
            html_kind=existing_file.content_json.get("html_kind") if existing_file else None,
        )
        content_json["status"] = STATUS_PUBLISHED
    except ValueError as exc:
        return build_tool_error_response(str(exc))

    try:
        if existing_file:
            source_name = filename.strip() or existing_file.original_name
            original_name = _sanitize_filename(source_name, content_json["title"])
            file_obj = _persist_html_file(
                conversation=conversation,
                user=user,
                content_json=content_json,
                original_name=original_name,
                file_obj=existing_file,
            )
            workspace_path = relocate_workspace_artifact(
                backend,
                source_path,
                str(file_obj.id),
            )
            action = "updated"
            updated = True
        else:
            original_name = _sanitize_filename(filename, content_json["title"])
            file_obj = _persist_html_file(
                conversation=conversation,
                user=user,
                content_json=content_json,
                original_name=original_name,
            )
            workspace_path = relocate_workspace_artifact(
                backend,
                source_path,
                str(file_obj.id),
            )
            action = "created"
            updated = False
    except Exception as exc:
        return build_tool_error_response(str(exc))

    _register_display(tool_call_id, file_obj, updated=updated)
    return _build_agent_tool_response(
        file_obj,
        action,
        workspace_path=workspace_path,
    )


@tool
def publish_html_artifact(
    path: str,
    title: str,
    runtime: ToolRuntime,
    subtitle: str = "",
    filename: str = "",
    file_id: str = "",
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Publish a validated workspace HTML file to the user.

    The file at `path` must exist under `/workspace/` (e.g. `/workspace/artifacts/_draft.html`
    for new reports, or `/workspace/artifacts/{file_id}.html` after hydrate).

    For new artifacts, omit `file_id`. For updates, pass the existing `file_id`.
    Call `validate_html_artifact` on `path` before publishing.
    """
    return run_publish_html_artifact(
        path,
        title,
        runtime,
        subtitle=subtitle,
        filename=filename,
        file_id=file_id,
        tool_call_id=tool_call_id,
    )
