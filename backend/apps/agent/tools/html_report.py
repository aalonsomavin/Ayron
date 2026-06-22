import json
import re
from datetime import date
from pathlib import Path
from typing import Annotated

from django.conf import settings
from langchain_core.tools import InjectedToolCallId, tool

from apps.agent.cancellation import check_agent_not_cancelled
from apps.agent.context import get_agent_conversation, get_agent_user
from apps.agent.tools.errors import build_tool_error_response
from apps.agent.tools.document_style import footer_attribution_text
from apps.agent.tools.html_insight import normalize_insight_markup
from apps.agent.tools.html_sanitize import normalize_agent_html, sanitize_html_report
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

AGENT_INSTRUCTION_AFTER_DRAFT_CREATE = (
    "Dashboard en borrador (no visible aún). "
    "Añade bloques con append_html_report_block y publica con publish_html_report. "
    "Tabs de página y filtros van arriba (inicio de ay-dash-inner, antes del contenido). "
    "No incluyas ay-dash-title, ay-dash-subtitle, ay-dash-eyebrow ni ay-dash-divider por ahora. "
    "Prefiere tabs por sección, filtros, tablas ordenables o calculadoras cuando el "
    "informe tenga varias vistas o datos comparables."
)

HTML_KIND_REPORT = "report"
HTML_KIND_DASHBOARD = "dashboard"
HTML_KINDS = {HTML_KIND_REPORT, HTML_KIND_DASHBOARD}

STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"

BUILD_MODE_COMPLETE = "complete"
BUILD_MODE_INCREMENTAL = "incremental"
BUILD_MODES = {BUILD_MODE_COMPLETE, BUILD_MODE_INCREMENTAL}

APPEND_TARGETS = {
    "grid": "ay-dash-grid",
    "tabs": "ay-dash-tab-panels",
    "prose": "ay-report-prose",
}

_ROOT_WRAPPER_RE = re.compile(
    r'\bclass="[^"]*\b(?:ay-dash-page|ay-report-prose)\b',
    re.IGNORECASE,
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


CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"


def _load_chart_css() -> str:
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "html_report_chart.css"
    return css_path.read_text(encoding="utf-8")


def _load_ayron_chart_js() -> str:
    js_path = Path(settings.BASE_DIR) / "static" / "js" / "ayron-chart.js"
    return js_path.read_text(encoding="utf-8")


def _load_ayron_dashboard_js() -> str:
    js_path = Path(settings.BASE_DIR) / "static" / "js" / "ayron-dashboard.js"
    return js_path.read_text(encoding="utf-8")


def _load_report_css(*, include_charts: bool = False) -> str:
    css = f"{_load_export_css()}\n{_load_dashboard_css()}"
    if include_charts:
        css = f"{css}\n{_load_chart_css()}"
    return css


def _body_has_charts(body_html: str) -> bool:
    return "ay-chart" in body_html


def _body_has_interactive_dashboard(body_html: str) -> bool:
    markers = (
        "ay-dash-tabs",
        "ay-dash-filter-bar",
        "ay-dash-filter-scope",
        "ay-dash-table--sortable",
        "ay-dash-calculator",
    )
    return any(marker in body_html for marker in markers)


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


def _report_dashboard_scripts(*, inline_mount: bool = False) -> str:
    ayron_js = _load_ayron_dashboard_js()
    mount = (
        "<script>document.addEventListener('DOMContentLoaded',function(){"
        "if(window.AyronDashboard){AyronDashboard.mountAll(document);}"
        "});</script>"
        if inline_mount
        else ""
    )
    return f"<script>{ayron_js}</script>{mount}"


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


def _export_runtime_scripts(body_html: str) -> str:
    scripts = ""
    if _body_has_charts(body_html):
        scripts += _report_chart_scripts(inline_mount=True)
    if _body_has_interactive_dashboard(body_html):
        scripts += _report_dashboard_scripts(inline_mount=True)
    return scripts


def build_preview_fragment(content_json: dict) -> str:
    body_html = content_json.get("body_html") or content_json.get("html") or ""
    body_html = normalize_insight_markup(body_html)
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
    body_html = normalize_insight_markup(body_html)
    wrapped_body = _wrap_export_body(body_html)
    include_charts = _body_has_charts(body_html)
    runtime_scripts = _export_runtime_scripts(body_html)
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
        f"{runtime_scripts}"
        "</body>"
        "</html>"
    )


def preview_html_for_file(content_json: dict | None, preview_html: str) -> str:
    if content_json and content_json.get("format") == "html":
        if content_json.get("body_html") or content_json.get("html"):
            return build_preview_fragment(content_json)
    return preview_html or ""


def _find_div_inner_bounds(html: str, after_open: int) -> tuple[int, int]:
    start = after_open
    depth = 1
    pos = start
    while pos < len(html) and depth > 0:
        next_open = html.find("<div", pos)
        next_close = html.find("</div>", pos)
        if next_close == -1:
            raise ValueError("Unclosed container div")
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                return start, next_close
            pos = next_close + 6
    raise ValueError("Could not locate end of container div")


def _find_div_container_bounds(html: str, container_class: str) -> tuple[int, int]:
    pattern = re.compile(
        rf'<div\b[^>]*\bclass="[^"]*\b{re.escape(container_class)}\b[^"]*"[^>]*>',
        re.IGNORECASE,
    )
    match = pattern.search(html)
    if not match:
        raise ValueError(f"Container .{container_class} not found in HTML")
    return _find_div_inner_bounds(html, match.end())


def _tabs_opening_is_page_level(opening_tag: str) -> bool:
    return (
        "ay-dash-tabs--section" not in opening_tag
        and "ay-dash-tabs--header" not in opening_tag
    )


def _find_page_tab_panels_bounds(html: str) -> tuple[int, int]:
    tabs_re = re.compile(
        r'<div\b[^>]*\bclass="[^"]*\bay-dash-tabs\b[^"]*"[^>]*>',
        re.IGNORECASE,
    )
    panels_re = re.compile(
        r'<div\b[^>]*\bclass="[^"]*\bay-dash-tab-panels\b[^"]*"[^>]*>',
        re.IGNORECASE,
    )
    for tabs_match in tabs_re.finditer(html):
        if not _tabs_opening_is_page_level(tabs_match.group(0)):
            continue
        panels_match = panels_re.search(html, tabs_match.end())
        if not panels_match:
            continue
        between = html[tabs_match.end() : panels_match.start()]
        if between.strip():
            continue
        return _find_div_inner_bounds(html, panels_match.end())
    return _find_div_container_bounds(html, "ay-dash-tab-panels")


def append_to_container(body_html: str, container_class: str, fragment: str) -> str:
    if container_class == "ay-dash-tab-panels":
        _inner_start, close_tag_start = _find_page_tab_panels_bounds(body_html)
    else:
        _inner_start, close_tag_start = _find_div_container_bounds(
            body_html, container_class
        )
    return body_html[:close_tag_start] + fragment + body_html[close_tag_start:]


def _validate_append_fragment(fragment: str) -> str:
    if _ROOT_WRAPPER_RE.search(fragment):
        raise ValueError(
            "Append fragment must not include root wrapper (.ay-dash-page or .ay-report-prose)"
        )
    cleaned = sanitize_html_report(fragment)
    if not cleaned.strip():
        raise ValueError("Append fragment is empty after sanitization")
    return cleaned


def _resolve_append_target(target: str) -> str:
    normalized = (target or "grid").strip().lower()
    container_class = APPEND_TARGETS.get(normalized)
    if not container_class:
        allowed = ", ".join(sorted(APPEND_TARGETS))
        raise ValueError(f"target must be one of: {allowed}")
    return container_class


def _merge_content_json(existing: dict, title, subtitle, html, html_kind=None) -> dict:
    merged = dict(existing)
    preserved_status = merged.get("status", STATUS_PUBLISHED)
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
    result = validate_html_report_content(
        merged.get("title", ""),
        merged.get("html") or merged.get("body_html", ""),
        merged.get("subtitle", ""),
        html_kind=kind,
        status=preserved_status,
    )
    return result


def _build_agent_tool_response(
    file_obj,
    action: str,
    *,
    draft: bool = False,
    agent_instruction: str | None = None,
) -> str:
    payload = {
        "ok": True,
        "action": action,
        "file_id": str(file_obj.id),
        "name": file_obj.original_name,
        "version": file_obj.version,
        "status": file_obj.content_json.get("status", STATUS_PUBLISHED),
        "agent_instruction": agent_instruction or AGENT_INSTRUCTION_AFTER_HTML_REPORT,
    }
    if draft:
        payload["draft"] = True
    return json.dumps(payload)


def _register_display(
    tool_call_id: str,
    file_obj,
    *,
    updated: bool = False,
    skip_chat_event: bool = False,
    force_created: bool = False,
) -> None:
    payload = serialize_file_for_ui(file_obj)
    payload["updated"] = updated and not force_created
    payload["status"] = file_obj.content_json.get("status", STATUS_PUBLISHED)
    if skip_chat_event or payload["status"] == STATUS_DRAFT:
        payload["skip_chat_event"] = True
    if force_created:
        payload["updated"] = False
    _HTML_REPORT_DISPLAY_REGISTRY[tool_call_id] = payload


def _resolve_build_mode(build_mode: str | None) -> str:
    normalized = (build_mode or BUILD_MODE_COMPLETE).strip().lower()
    if normalized not in BUILD_MODES:
        allowed = ", ".join(sorted(BUILD_MODES))
        raise ValueError(f"build_mode must be one of: {allowed}")
    return normalized


def _persist_html_file(
    *,
    conversation,
    user,
    content_json: dict,
    original_name: str,
    file_obj=None,
):
    export_html = build_export_html(content_json)
    preview_html = build_preview_fragment(content_json)
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
    return update_generated_file(
        file_obj=file_obj,
        content_json=content_json,
        file_bytes=export_html.encode("utf-8"),
        preview_html=preview_html,
    )


@tool
def create_html_report(
    title: str,
    html: str,
    subtitle: str = "",
    filename: str = "",
    html_kind: str = "",
    build_mode: str = "complete",
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

    For large dashboards, use `build_mode="incremental"`: creates a draft shell
    (not visible to the user), then call `append_html_report_block` for each
    section and `publish_html_report` when done. Put page-level tabs and filter
    bars at the top of the dashboard (start of `.ay-dash-inner`), before
    insight/KPI/table content — see GUIDELINES. Do not include page title,
    subtitle, eyebrow or divider markup for now.

    For charts, embed `.ay-chart` blocks with a JSON payload in
    `<script type="application/json">` (see GUIDELINES). Do not use `<script>`
    for JavaScript.

    Insight blocks must use the exact structure from `starter-dashboard.html`
    (`.ay-dash-insight-head` + empty `.ay-dash-insight-logo`). Ayron injects
    the brand mark automatically; never use custom icons, emoji, or symbols.

    Pass the report body as `html`: a body fragment with semantic markup. You may
    pass a full document (<!DOCTYPE html>...) if needed. Tables, SVG diagrams, and
    <pre><code> are allowed; no <script>.

    Set `title` for file metadata. Use `subtitle` for one line of context.
    Use `filename` like `<topic>-<kind>.html`. Do not repeat report content in chat.

    To modify an existing report later, use update_html_report with the same file_id.
    """
    check_agent_not_cancelled()
    conversation = get_agent_conversation()
    user = get_agent_user()
    if conversation is None or user is None:
        return build_tool_error_response("No conversation context")

    try:
        kind = html_kind.strip() if html_kind else None
        mode = _resolve_build_mode(build_mode)
        content_json = validate_html_report_content(title, html, subtitle, html_kind=kind)
        if mode == BUILD_MODE_INCREMENTAL:
            if content_json["html_kind"] != HTML_KIND_DASHBOARD:
                raise ValueError("build_mode=incremental is only valid for dashboards")
            content_json["status"] = STATUS_DRAFT
        else:
            content_json["status"] = STATUS_PUBLISHED
    except ValueError as exc:
        return build_tool_error_response(str(exc))

    try:
        original_name = _sanitize_filename(filename, content_json["title"])
        file_obj = _persist_html_file(
            conversation=conversation,
            user=user,
            content_json=content_json,
            original_name=original_name,
        )
    except Exception as exc:
        return build_tool_error_response(str(exc))

    is_draft = content_json["status"] == STATUS_DRAFT
    _register_display(tool_call_id, file_obj, skip_chat_event=is_draft)
    return _build_agent_tool_response(
        file_obj,
        "created",
        draft=is_draft,
        agent_instruction=AGENT_INSTRUCTION_AFTER_DRAFT_CREATE if is_draft else None,
    )


@tool
def append_html_report_block(
    file_id: str,
    html: str,
    target: str = "grid",
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Append a sanitized HTML block to a draft dashboard or report.

    Use after `create_html_report(..., build_mode="incremental")`. The user does
    not see updates until `publish_html_report`.

    `target`:
    - `grid`: append inside `.ay-dash-grid` (KPI cards, tables, charts, **tabs de sección**)
    - `tabs`: append a `.ay-dash-tab-panel` inside the **page-level** `.ay-dash-tab-panels` only (capítulos grandes). El contenedor de tabs va **arriba** en el shell, al inicio de `.ay-dash-inner`. No uses esto para años, regiones ni sub-vistas — esas van en `.ay-dash-tabs--section` con `target="grid"`.
    - `prose`: append inside `.ay-report-prose`

    Do not include root wrappers (`.ay-dash-page`, `.ay-report-prose`) in `html`.
    """
    check_agent_not_cancelled()
    conversation = get_agent_conversation()
    if conversation is None:
        return build_tool_error_response("No conversation context")

    file_obj = get_file_for_conversation(file_id, conversation)
    if file_obj is None or file_obj.format_key != "html":
        return build_tool_error_response("HTML report not found in this conversation")

    if file_obj.content_json.get("status") != STATUS_DRAFT:
        return build_tool_error_response(
            "Can only append to draft files; use update_html_report on published files"
        )

    try:
        container_class = _resolve_append_target(target)
        fragment = _validate_append_fragment(html)
        body_html = file_obj.content_json.get("body_html") or file_obj.content_json.get("html", "")
        updated_body = append_to_container(body_html, container_class, fragment)
        content_json = validate_html_report_content(
            file_obj.content_json.get("title", ""),
            updated_body,
            file_obj.content_json.get("subtitle", ""),
            html_kind=file_obj.content_json.get("html_kind"),
            status=STATUS_DRAFT,
        )
    except ValueError as exc:
        return build_tool_error_response(str(exc))

    try:
        file_obj = _persist_html_file(
            conversation=conversation,
            user=get_agent_user(),
            content_json=content_json,
            original_name=file_obj.original_name,
            file_obj=file_obj,
        )
    except Exception as exc:
        return build_tool_error_response(str(exc))

    return json.dumps(
        {
            "ok": True,
            "action": "appended",
            "file_id": str(file_obj.id),
            "version": file_obj.version,
            "draft": True,
            "target": target.strip().lower() or "grid",
        }
    )


@tool
def publish_html_report(
    file_id: str,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Publish a draft HTML dashboard so it becomes visible to the user.

    Call after all `append_html_report_block` steps are complete.
    """
    check_agent_not_cancelled()
    conversation = get_agent_conversation()
    if conversation is None:
        return build_tool_error_response("No conversation context")

    file_obj = get_file_for_conversation(file_id, conversation)
    if file_obj is None or file_obj.format_key != "html":
        return build_tool_error_response("HTML report not found in this conversation")

    if file_obj.content_json.get("status") != STATUS_DRAFT:
        return build_tool_error_response("File is already published")

    if file_obj.content_json.get("html_kind") != HTML_KIND_DASHBOARD:
        return build_tool_error_response("Only draft dashboards can be published with this tool")

    content_json = dict(file_obj.content_json)
    content_json["status"] = STATUS_PUBLISHED

    try:
        file_obj = _persist_html_file(
            conversation=conversation,
            user=get_agent_user(),
            content_json=content_json,
            original_name=file_obj.original_name,
            file_obj=file_obj,
        )
    except Exception as exc:
        return build_tool_error_response(str(exc))

    _register_display(tool_call_id, file_obj, force_created=True)
    return _build_agent_tool_response(file_obj, "published")


@tool
def get_html_report(file_id: str) -> str:
    """Read the HTML report content by file_id.

    Returns title, subtitle, and the stored `html` for editing.
    Call before update_html_report when you need the current markup.
    """
    conversation = get_agent_conversation()
    if conversation is None:
        return build_tool_error_response("No conversation context")

    file_obj = get_file_for_conversation(file_id, conversation)
    if file_obj is None or file_obj.format_key != "html":
        return build_tool_error_response("HTML report not found in this conversation")

    body_html = file_obj.content_json.get("body_html") or file_obj.content_json.get("html", "")
    payload = {
        "ok": True,
        **serialize_file_for_agent(file_obj),
        "title": file_obj.content_json.get("title", ""),
        "subtitle": file_obj.content_json.get("subtitle", ""),
        "html_kind": file_obj.content_json.get("html_kind")
        or infer_html_kind(body_html),
        "status": file_obj.content_json.get("status", STATUS_PUBLISHED),
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
    `html_kind` is re-inferred when `html` changes. Only works on published files.
    """
    check_agent_not_cancelled()
    conversation = get_agent_conversation()
    if conversation is None:
        return build_tool_error_response("No conversation context")

    file_obj = get_file_for_conversation(file_id, conversation)
    if file_obj is None or file_obj.format_key != "html":
        return build_tool_error_response("HTML report not found in this conversation")

    if file_obj.content_json.get("status") == STATUS_DRAFT:
        return build_tool_error_response(
            "Cannot update a draft file; use append_html_report_block or publish_html_report"
        )

    try:
        kind = html_kind.strip() if isinstance(html_kind, str) and html_kind.strip() else None
        content_json = _merge_content_json(
            file_obj.content_json, title, subtitle, html, html_kind=kind
        )
        content_json["status"] = STATUS_PUBLISHED
    except ValueError as exc:
        return build_tool_error_response(str(exc))

    try:
        file_obj = _persist_html_file(
            conversation=conversation,
            user=get_agent_user(),
            content_json=content_json,
            original_name=file_obj.original_name,
            file_obj=file_obj,
        )
    except Exception as exc:
        return build_tool_error_response(str(exc))

    _register_display(tool_call_id, file_obj, updated=True)
    return _build_agent_tool_response(file_obj, "updated")
