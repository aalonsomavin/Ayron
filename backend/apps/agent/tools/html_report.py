import json
import re
from datetime import date
from pathlib import Path
from typing import Annotated

from django.conf import settings
from langchain_core.tools import InjectedToolCallId, tool

from apps.agent.context import get_agent_conversation, get_agent_user
from apps.agent.tools.document_style import footer_attribution_text
from apps.agent.tools.html_sanitize import normalize_agent_html
from apps.files.models import HTML_MIME
from apps.files.services import (
    escape_preview_text as esc,
    get_file_for_conversation,
    save_generated_file,
    serialize_file_for_agent,
    serialize_file_for_ui,
    update_generated_file,
)

_HTML_REPORT_DISPLAY_REGISTRY: dict[str, dict] = {}

AGENT_INSTRUCTION_AFTER_HTML_REPORT = (
    "El reporte ya está visible en el chat del usuario. "
    "NO repitas el contenido del informe en tu siguiente mensaje. "
    "Solo añade una frase breve si aporta contexto, o termina sin texto."
)


def pop_html_report_display(tool_call_id: str | None) -> dict | None:
    if not tool_call_id:
        return None
    return _HTML_REPORT_DISPLAY_REGISTRY.pop(tool_call_id, None)


def _sanitize_filename(name: str, fallback: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name).strip()
    if not cleaned:
        cleaned = fallback
    if not cleaned.lower().endswith(".html"):
        cleaned = f"{cleaned}.html"
    return cleaned[:200]


HTML_KIND_REPORT = "report"
HTML_KIND_DASHBOARD = "dashboard"
HTML_KINDS = {HTML_KIND_REPORT, HTML_KIND_DASHBOARD}


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
) -> dict:
    if not title or not str(title).strip():
        raise ValueError("title is required")
    normalized = normalize_agent_html(html)
    body_html = normalized["body_html"]
    return {
        "format": "html",
        "html_kind": resolve_html_kind(body_html, html_kind),
        "title": str(title).strip(),
        "subtitle": str(subtitle or "").strip(),
        "html": normalized["html"],
        "body_html": body_html,
        "full_document": normalized["full_document"],
    }


def _load_export_css() -> str:
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "html_report_export.css"
    return css_path.read_text(encoding="utf-8")


def _load_dashboard_css() -> str:
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "html_report_dashboard.css"
    return css_path.read_text(encoding="utf-8")


CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"


def _load_chart_css() -> str:
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "html_report_chart.css"
    return css_path.read_text(encoding="utf-8")


def _load_ayron_chart_js() -> str:
    js_path = Path(settings.BASE_DIR) / "static" / "js" / "ayron-chart.js"
    return js_path.read_text(encoding="utf-8")


def _load_report_css(*, include_charts: bool = False) -> str:
    css = f"{_load_export_css()}\n{_load_dashboard_css()}"
    if include_charts:
        css = f"{css}\n{_load_chart_css()}"
    return css


def _body_has_charts(body_html: str) -> bool:
    return "ay-chart" in body_html


def _report_chart_scripts(*, inline_mount: bool = False) -> str:
    ayron_js = _load_ayron_chart_js()
    mount = (
        "<script>document.addEventListener('DOMContentLoaded',function(){"
        "if(window.AyronChart){AyronChart.mountAll(document);}"
        "});</script>"
        if inline_mount
        else ""
    )
    return (
        f'<script src="{CHART_JS_CDN}"></script>'
        f"<script>{ayron_js}</script>"
        f"{mount}"
    )


def _report_font_links() -> str:
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
        "?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap\">"
    )


def _report_styles_html(*, include_charts: bool = False) -> str:
    return f"<style>{_load_report_css(include_charts=include_charts)}</style>"


def _footer_html() -> str:
    return f'<footer class="ay-html-report__footer">{esc(footer_attribution_text(date.today()))}</footer>'


def _uses_report_shell(body_html: str) -> bool:
    return "ay-dash-page" in body_html or "ay-report-prose" in body_html


def _wrap_export_body(body_html: str) -> str:
    if _uses_report_shell(body_html):
        return f"{body_html}{_footer_html()}"
    return f'<div class="ay-html-report">{body_html}{_footer_html()}</div>'


def build_preview_fragment(content_json: dict) -> str:
    body_html = content_json.get("body_html") or content_json.get("html") or ""
    include_charts = _body_has_charts(body_html)
    return (
        f"{_report_font_links()}"
        f"{_report_styles_html(include_charts=include_charts)}"
        f'<div class="ay-html-report-preview">{body_html}</div>'
    )


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
    wrapped_body = _wrap_export_body(body_html)
    include_charts = _body_has_charts(body_html)
    chart_scripts = _report_chart_scripts(inline_mount=True) if include_charts else ""
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
        f"{chart_scripts}"
        "</body>"
        "</html>"
    )


def preview_html_for_file(content_json: dict | None, preview_html: str) -> str:
    if content_json and content_json.get("format") == "html":
        if content_json.get("body_html") or content_json.get("html"):
            return build_preview_fragment(content_json)
    return preview_html or ""


def _merge_content_json(existing: dict, title, subtitle, html, html_kind=None) -> dict:
    merged = dict(existing)
    if title is not None:
        merged["title"] = str(title).strip()
    if subtitle is not None:
        merged["subtitle"] = str(subtitle).strip()
    if html is not None:
        normalized = normalize_agent_html(html)
        merged["html"] = normalized["html"]
        merged["body_html"] = normalized["body_html"]
        merged["full_document"] = normalized["full_document"]
        merged.pop("html_kind", None)
    kind = html_kind if html_kind is not None else merged.get("html_kind")
    return validate_html_report_content(
        merged.get("title", ""),
        merged.get("html") or merged.get("body_html", ""),
        merged.get("subtitle", ""),
        html_kind=kind,
    )


def _build_agent_tool_response(file_obj, action: str) -> str:
    return json.dumps(
        {
            "ok": True,
            "action": action,
            "file_id": str(file_obj.id),
            "name": file_obj.original_name,
            "version": file_obj.version,
            "agent_instruction": AGENT_INSTRUCTION_AFTER_HTML_REPORT,
        }
    )


def _register_display(tool_call_id: str, file_obj, updated: bool = False) -> None:
    payload = serialize_file_for_ui(file_obj)
    payload["updated"] = updated
    _HTML_REPORT_DISPLAY_REGISTRY[tool_call_id] = payload


@tool
def create_html_report(
    title: str,
    html: str,
    subtitle: str = "",
    filename: str = "",
    html_kind: str = "",
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Create an HTML report or dashboard for the user in the chat.

    Read `/skills/html-reports/GUIDELINES.md` before writing HTML. Use shared
    classes (`ay-dash-*` for dashboards, `ay-report-prose` for explainers) — do
    not duplicate system CSS or Google Fonts in the fragment. Ayron injects fonts
    and stylesheet automatically.

    Two deliverable types (inferred from markup, or set `html_kind` explicitly):
    - `report`: prose document (`.ay-report-prose`), opens in the artifact panel,
      exportable as PDF.
    - `dashboard`: analytics layout (`.ay-dash-page`), opens expanded on click.

    For charts, embed `.ay-chart` blocks with a JSON payload in
    `<script type="application/json">` (see GUIDELINES). Do not use `<script>`
    for JavaScript.

    Pass the report body as `html`: a body fragment with semantic markup. You may
    pass a full document (<!DOCTYPE html>...) if needed. Tables, SVG diagrams, and
    <pre><code> are allowed; no <script>.

    Set `title` for file metadata. Use `subtitle` for one line of context.
    Use `filename` like `<topic>-<kind>.html`. Do not repeat report content in chat.

    To modify an existing report later, use update_html_report with the same file_id.
    """
    conversation = get_agent_conversation()
    user = get_agent_user()
    if conversation is None or user is None:
        return json.dumps({"ok": False, "error": "No conversation context"})

    try:
        kind = html_kind.strip() if html_kind else None
        content_json = validate_html_report_content(title, html, subtitle, html_kind=kind)
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})

    original_name = _sanitize_filename(filename, content_json["title"])
    export_html = build_export_html(content_json)
    preview_html = build_preview_fragment(content_json)

    file_obj = save_generated_file(
        conversation=conversation,
        user=user,
        original_name=original_name,
        content_json=content_json,
        file_bytes=export_html.encode("utf-8"),
        preview_html=preview_html,
        mime_type=HTML_MIME,
    )
    _register_display(tool_call_id, file_obj, updated=False)
    return _build_agent_tool_response(file_obj, "created")


@tool
def get_html_report(file_id: str) -> str:
    """Read the HTML report content by file_id.

    Returns title, subtitle, and the stored `html` for editing.
    Call before update_html_report when you need the current markup.
    """
    conversation = get_agent_conversation()
    if conversation is None:
        return json.dumps({"ok": False, "error": "No conversation context"})

    file_obj = get_file_for_conversation(file_id, conversation)
    if file_obj is None or file_obj.format_key != "html":
        return json.dumps({"ok": False, "error": "HTML report not found in this conversation"})

    body_html = file_obj.content_json.get("body_html") or file_obj.content_json.get("html", "")
    payload = {
        "ok": True,
        **serialize_file_for_agent(file_obj),
        "title": file_obj.content_json.get("title", ""),
        "subtitle": file_obj.content_json.get("subtitle", ""),
        "html_kind": file_obj.content_json.get("html_kind")
        or infer_html_kind(body_html),
        "html": file_obj.content_json.get("html") or body_html,
    }
    return json.dumps(payload)


@tool
def update_html_report(
    file_id: str,
    title: str | None = None,
    subtitle: str | None = None,
    html: str | None = None,
    html_kind: str | None = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Update an existing HTML report by file_id.

    Provide only the fields you want to change. `html` replaces all markup when provided.
    `html_kind` is re-inferred when `html` changes.
    """
    conversation = get_agent_conversation()
    if conversation is None:
        return json.dumps({"ok": False, "error": "No conversation context"})

    file_obj = get_file_for_conversation(file_id, conversation)
    if file_obj is None or file_obj.format_key != "html":
        return json.dumps({"ok": False, "error": "HTML report not found in this conversation"})

    try:
        kind = html_kind.strip() if isinstance(html_kind, str) and html_kind.strip() else None
        content_json = _merge_content_json(
            file_obj.content_json, title, subtitle, html, html_kind=kind
        )
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})

    export_html = build_export_html(content_json)
    preview_html = build_preview_fragment(content_json)
    file_obj = update_generated_file(
        file_obj=file_obj,
        content_json=content_json,
        file_bytes=export_html.encode("utf-8"),
        preview_html=preview_html,
    )
    _register_display(tool_call_id, file_obj, updated=True)
    return _build_agent_tool_response(file_obj, "updated")
