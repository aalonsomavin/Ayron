from __future__ import annotations

import hashlib
import html
import re
from io import BytesIO

from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone
from django.utils.timesince import timesince

from apps.chat.models import AgentEvent, Conversation, Message
from apps.files.models import DOCX_MIME, HTML_MIME, XLSX_MIME, File, SavedDashboard


def _section_count(content_json: dict) -> int:
    return len(content_json.get("sections") or [])


def _html_kind(content_json: dict) -> str:
    kind = content_json.get("html_kind")
    if kind in ("report", "dashboard"):
        return kind
    body_html = content_json.get("body_html") or content_json.get("html") or ""
    if "ay-dash-page" in body_html:
        return "dashboard"
    return "report"


def _sheet_count(content_json: dict) -> int:
    return len(content_json.get("sheets") or [])


def _file_meta(content_json: dict) -> str:
    format_key = content_json.get("format", "docx")
    if format_key == "html":
        if _html_kind(content_json) == "dashboard":
            return "Dashboard"
        return "Report · HTML"
    if format_key == "xlsx":
        count = _sheet_count(content_json)
        if count == 1:
            return "Spreadsheet · 1 hoja"
        return f"Spreadsheet · {count} hojas"
    sections = _section_count(content_json)
    page_word = "sección" if sections == 1 else "secciones"
    return f"Document · {sections} {page_word}"


def _file_ext(content_json: dict, mime_type: str) -> str:
    format_key = content_json.get("format")
    if format_key == "html" or mime_type == HTML_MIME:
        return "HTML"
    if format_key == "xlsx" or mime_type == XLSX_MIME:
        return "XLSX"
    return "DOCX"


def _file_kind(content_json: dict) -> str:
    format_key = content_json.get("format", "docx")
    if format_key == "html" and _html_kind(content_json) == "dashboard":
        return "dashboard"
    if format_key == "xlsx":
        return "sheet"
    return "doc"


def _display_name(original_name: str, content_json: dict) -> str:
    if content_json.get("format") == "html":
        fallback = content_json.get("title") or "report"
        name = _normalize_html_filename(original_name, fallback)
    else:
        name = original_name or ""
    if _file_kind(content_json) == "dashboard" and name.lower().endswith(".html"):
        return name[:-5]
    return name


def normalize_file_payload_for_ui(payload: dict) -> dict:
    normalized = dict(payload)
    meta = normalized.get("meta") or ""
    is_dashboard = (
        normalized.get("kind") == "dashboard"
        or meta == "Dashboard"
        or meta.startswith("Dashboard ·")
    )
    if not is_dashboard:
        return normalized
    normalized["kind"] = "dashboard"
    normalized["meta"] = "Dashboard"
    name = normalized.get("name") or ""
    if name.lower().endswith(".html"):
        normalized["name"] = name[:-5]
    return normalized


def hydrate_file_payload_for_ui(payload: dict, *, conversation_id=None, user=None) -> dict:
    normalized = normalize_file_payload_for_ui(dict(payload))
    file_id = normalized.get("file_id")
    if not file_id:
        return normalized

    qs = File.objects.filter(id=file_id)
    if conversation_id is not None:
        qs = qs.filter(conversation_id=conversation_id)
    file_obj = qs.first()
    if file_obj is None:
        return normalized

    fresh = serialize_file_for_ui(file_obj, user=user)
    if normalized.get("updated"):
        fresh["updated"] = True
    return fresh


CONTEXT_UPDATE_ERROR = (
    "Este archivo es contexto del usuario; crea un entregable nuevo con "
    "create_spreadsheet, create_document o publish_html_artifact."
)


def serialize_file_for_ui(file_obj: File, *, user=None) -> dict:
    format_key = file_obj.format_key
    payload = {
        "file_id": str(file_obj.id),
        "name": _display_name(file_obj.original_name, file_obj.content_json),
        "ext": _file_ext(file_obj.content_json, file_obj.mime_type),
        "format": format_key,
        "kind": _file_kind(file_obj.content_json),
        "role": _file_role(file_obj.content_json),
        "mime": file_obj.mime_type,
        "meta": _file_meta(file_obj.content_json),
        "version": file_obj.version,
        "size_bytes": file_obj.size_bytes,
        "download_url": f"/files/{file_obj.id}/download/",
        "preview_url": f"/files/{file_obj.id}/preview/",
    }
    if format_key == "html":
        payload["download_pdf_url"] = f"/files/{file_obj.id}/download/pdf/"
        payload["open_expanded"] = _html_kind(file_obj.content_json) == "dashboard"
    if user is not None and payload["kind"] == "dashboard":
        payload["saved"] = is_dashboard_saved(user, file_obj.id)
    return payload


def _file_source(content_json: dict) -> str:
    return content_json.get("source") or "generated"


def _file_role(content_json: dict) -> str:
    role = content_json.get("role")
    if role in ("context", "deliverable"):
        return role
    if _file_source(content_json) == "upload":
        return "context"
    return "deliverable"


def is_context_file(content_json: dict) -> bool:
    return _file_role(content_json) == "context"


def is_deliverable_file(content_json: dict) -> bool:
    return _file_role(content_json) == "deliverable"


def context_update_error(file_obj: File) -> str | None:
    if is_context_file(file_obj.content_json):
        return CONTEXT_UPDATE_ERROR
    return None


def _source_label(source: str) -> str:
    if source == "upload":
        return "subido"
    return "generado"


def _read_tool_for_format(format_key: str) -> str:
    if format_key == "xlsx":
        return "get_spreadsheet"
    if format_key == "html":
        return "hydrate_html_artifact"
    return "get_document"


FILE_INDEX_READ_INSTRUCTIONS = """\
Para leer archivos existentes:
- Excel (.xlsx): get_spreadsheet(file_id)
- Word (.docx): get_document(file_id)
- HTML: hydrate_html_artifact(file_id) o list_conversation_files
No inventes datos; lee el archivo antes de analizarlo si el usuario lo adjuntó o lo referencia."""


def serialize_file_for_agent(file_obj: File) -> dict:
    source = _file_source(file_obj.content_json)
    return {
        "file_id": str(file_obj.id),
        "name": file_obj.original_name,
        "format": file_obj.format_key,
        "version": file_obj.version,
        "updated_at": file_obj.updated_at.isoformat(),
        "summary": file_obj.content_json.get("title", ""),
        "status": file_obj.content_json.get("status", "published"),
        "source": source,
        "role": _file_role(file_obj.content_json),
    }


def get_agent_file_index(conversation: Conversation) -> list[dict]:
    files = File.objects.filter(conversation=conversation).order_by("created_at")
    return [serialize_file_for_agent(file_obj) for file_obj in files]


def format_agent_file_index_block(conversation: Conversation) -> str:
    entries = get_agent_file_index(conversation)
    if not entries:
        return ""
    context_entries = [entry for entry in entries if entry.get("role") == "context"]
    deliverable_entries = [entry for entry in entries if entry.get("role") != "context"]
    lines: list[str] = []

    if context_entries:
        lines.extend(["## Archivos subidos por el usuario", ""])
        for entry in context_entries:
            format_label = entry.get("format", "docx").upper()
            read_tool = _read_tool_for_format(entry.get("format", "docx"))
            lines.append(
                f"- file_id={entry['file_id']} · {entry['name']} · {format_label} · "
                f"v{entry['version']} → {read_tool} (solo lectura)"
            )
        lines.append("")

    if deliverable_entries:
        lines.extend(["## Archivos generados por el agente", ""])
        for entry in deliverable_entries:
            format_label = entry.get("format", "docx").upper()
            lines.append(
                f"- file_id={entry['file_id']} · {entry['name']} · {format_label} · "
                f"v{entry['version']} · {entry['summary'] or 'sin título'}"
            )
        lines.append("")

    lines.extend([FILE_INDEX_READ_INSTRUCTIONS, ""])
    return "\n".join(lines)


def format_user_attachments_block(user_message: Message | None) -> str:
    if user_message is None:
        return ""
    events = AgentEvent.objects.filter(
        message=user_message,
        event_type=AgentEvent.EventType.FILE_CREATED,
    ).order_by("sequence_number")
    if not events.exists():
        return ""

    lines = [
        "## Contexto adjunto en este mensaje",
        "",
        "El usuario adjuntó estos archivos como contexto (solo lectura). "
        "Léelos con la tool indicada; si debe haber un entregable, genera un artifact "
        "nuevo con create_spreadsheet, create_document o publish_html_artifact:",
        "",
    ]
    for event in events:
        file_id = event.payload.get("file_id")
        if not file_id:
            continue
        file_obj = File.objects.filter(
            id=file_id,
            conversation_id=user_message.conversation_id,
        ).first()
        if file_obj is None:
            continue
        format_label = file_obj.format_key.upper()
        read_tool = _read_tool_for_format(file_obj.format_key)
        lines.append(
            f"- file_id={file_obj.id} · {file_obj.original_name} · {format_label} · "
            f"contexto → {read_tool}"
        )
    if len(lines) <= 4:
        return ""
    lines.append("")
    return "\n".join(lines)


def get_context_attachments_for_message(user_message: Message | None) -> list[dict]:
    if user_message is None:
        return []
    events = AgentEvent.objects.filter(
        message=user_message,
        event_type=AgentEvent.EventType.FILE_CREATED,
    ).order_by("sequence_number")
    attachments: list[dict] = []
    for event in events:
        file_id = event.payload.get("file_id")
        if not file_id:
            continue
        file_obj = File.objects.filter(
            id=file_id,
            conversation_id=user_message.conversation_id,
        ).first()
        if file_obj is None or not is_context_file(file_obj.content_json):
            continue
        attachments.append(
            {
                "file_id": str(file_obj.id),
                "format": file_obj.format_key,
                "role": "context",
            }
        )
    return attachments


def save_generated_file(
    conversation: Conversation,
    user,
    original_name: str,
    content_json: dict,
    file_bytes: bytes,
    preview_html: str,
    mime_type: str = DOCX_MIME,
) -> File:
    from apps.files.models import MIME_EXTENSIONS

    ext = MIME_EXTENSIONS.get(mime_type, ".bin")
    stored_content = dict(content_json)
    stored_content["role"] = "deliverable"
    stored_content["source"] = "generated"
    file_obj = File(
        uploaded_by=user,
        conversation=conversation,
        original_name=original_name,
        mime_type=mime_type,
        content_json=stored_content,
        preview_html=preview_html,
        size_bytes=len(file_bytes),
    )
    file_obj.file.save(
        f"{file_obj.id}{ext}",
        ContentFile(file_bytes),
        save=False,
    )
    file_obj.save()
    return file_obj


def save_uploaded_file(
    conversation: Conversation,
    user,
    original_name: str,
    file_bytes: bytes,
    parsed,
) -> File:
    from apps.files.models import MIME_EXTENSIONS

    content_json = dict(parsed.content_json)
    content_json["source"] = "upload"
    content_json["role"] = "context"
    mime_type = parsed.mime_type
    ext = MIME_EXTENSIONS.get(mime_type, ".bin")
    file_obj = File(
        uploaded_by=user,
        conversation=conversation,
        original_name=original_name,
        mime_type=mime_type,
        content_json=content_json,
        preview_html=parsed.preview_html,
        size_bytes=len(file_bytes),
    )
    file_obj.file.save(
        f"{file_obj.id}{ext}",
        ContentFile(file_bytes),
        save=False,
    )
    file_obj.save()
    return file_obj


def update_generated_file(
    file_obj: File,
    content_json: dict,
    file_bytes: bytes,
    preview_html: str,
) -> File:
    from apps.files.models import MIME_EXTENSIONS

    ext = MIME_EXTENSIONS.get(file_obj.mime_type, ".bin")
    file_obj.content_json = content_json
    file_obj.preview_html = preview_html
    file_obj.size_bytes = len(file_bytes)
    file_obj.version += 1
    file_obj.file.save(
        f"{file_obj.id}{ext}",
        ContentFile(file_bytes),
        save=False,
    )
    file_obj.save()
    return file_obj


def open_file_stream(file_obj: File) -> BytesIO:
    if file_obj.format_key == "docx":
        from apps.agent.tools.document import build_docx

        return BytesIO(build_docx(file_obj.content_json))
    if file_obj.format_key == "xlsx":
        if is_context_file(file_obj.content_json) and file_obj.version == 1:
            file_obj.file.open("rb")
            try:
                return BytesIO(file_obj.file.read())
            finally:
                file_obj.file.close()
        from apps.agent.tools.spreadsheet import build_xlsx

        return BytesIO(build_xlsx(file_obj.content_json))

    file_obj.file.open("rb")
    try:
        return BytesIO(file_obj.file.read())
    finally:
        file_obj.file.close()


def get_file_for_user(file_id: str, user) -> File | None:
    try:
        return File.objects.get(id=file_id, uploaded_by=user)
    except File.DoesNotExist:
        return None


def get_file_for_conversation(file_id: str, conversation: Conversation) -> File | None:
    try:
        return File.objects.get(id=file_id, conversation=conversation)
    except File.DoesNotExist:
        return None


def escape_preview_text(value: str) -> str:
    return html.escape(value or "")


def _normalize_html_filename(name: str, fallback: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", str(name or "")).strip()
    html_pos = cleaned.lower().find(".html")
    if html_pos >= 0:
        cleaned = cleaned[: html_pos + 5]
    if not cleaned:
        cleaned = re.sub(r'[<>:"/\\|?*]', "", str(fallback or "")).strip()
    if not cleaned:
        cleaned = "report"
    if not cleaned.lower().endswith(".html"):
        cleaned = f"{cleaned}.html"
    return cleaned[:200]


def _sanitize_dashboard_filename(name: str, fallback: str) -> str:
    return _normalize_html_filename(name, fallback)


def rename_dashboard_file(file_obj: File, name: str) -> File:
    from apps.agent.tools.html_report import build_export_html
    from apps.files.models import MIME_EXTENSIONS

    if _file_kind(file_obj.content_json) != "dashboard":
        raise ValueError("Only dashboards can be renamed")

    raw = (name or "").strip()
    if not raw:
        raise ValueError("name is required")

    fallback = file_obj.content_json.get("title") or "dashboard"
    original_name = _sanitize_dashboard_filename(raw, fallback)
    title = original_name[:-5] if original_name.lower().endswith(".html") else original_name

    content_json = dict(file_obj.content_json)
    content_json["title"] = title
    export_html = build_export_html(content_json)
    file_bytes = export_html.encode("utf-8")

    ext = MIME_EXTENSIONS.get(file_obj.mime_type, ".bin")
    file_obj.original_name = original_name
    file_obj.content_json = content_json
    file_obj.size_bytes = len(file_bytes)
    file_obj.file.save(
        f"{file_obj.id}{ext}",
        ContentFile(file_bytes),
        save=False,
    )
    file_obj.save()
    return file_obj


def _user_display_name(user) -> str:
    full_name = user.get_full_name().strip()
    if full_name:
        return full_name
    return user.get_username()


def _user_initials(user) -> str:
    name = _user_display_name(user)
    parts = [part for part in name.split() if part]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    if parts:
        return parts[0][:2].upper()
    return "?"


def _relative_date_label(dt) -> str:
    now = timezone.now()
    if dt.date() == now.date():
        return "Actualizado hoy"
    delta = timesince(dt, now)
    first = delta.split(",")[0].strip()
    if first.startswith("0 "):
        return "Actualizado hace un momento"
    return f"Actualizado hace {first}"


def _spark_series_for_file(file_id) -> list[int]:
    digest = hashlib.md5(str(file_id).encode()).hexdigest()
    values = []
    seed = int(digest[:8], 16)
    value = 40 + (seed % 20)
    for i in range(10):
        seed = (seed * 1103515245 + 12345 + i) & 0x7FFFFFFF
        delta = (seed % 17) - 8
        value = max(18, min(98, value + delta))
        values.append(value)
    return values


def _sparkline_paths(series: list[int], width: int = 320, height: int = 108, pad: int = 4) -> dict:
    if len(series) < 2:
        series = [40, 52, 48, 63, 70, 66, 82, 90, 86, 98]
    mx = max(series)
    mn = min(series)
    n = len(series)

    def xs(i: int) -> float:
        return pad + (i / (n - 1)) * (width - 2 * pad)

    def ys(v: int) -> float:
        return height - pad - ((v - mn) / (mx - mn or 1)) * (height - 2 * pad)

    line_path = f"M{xs(0):.1f},{ys(series[0]):.1f}"
    for i in range(1, n):
        line_path += f" L{xs(i):.1f},{ys(series[i]):.1f}"
    area_path = f"{line_path} L{xs(n - 1):.1f},{height - pad:.1f} L{xs(0):.1f},{height - pad:.1f} Z"
    return {"line": line_path, "area": area_path}


def _spark_tint_for_file(file_id) -> str:
    palette = ["#3b6ef6", "#16a34a", "#8b5cf6", "#d97706", "#0d9aa8", "#e1568f"]
    digest = hashlib.md5(str(file_id).encode()).hexdigest()
    return palette[int(digest[:2], 16) % len(palette)]


def is_dashboard_saved(user, file_id) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return SavedDashboard.objects.filter(user=user, file_id=file_id).exists()


def save_dashboard(user, file_obj: File) -> SavedDashboard:
    if _file_kind(file_obj.content_json) != "dashboard":
        raise ValueError("Only dashboards can be saved")
    saved, _ = SavedDashboard.objects.get_or_create(user=user, file=file_obj)
    return saved


def unsave_dashboard(user, file_id) -> bool:
    deleted, _ = SavedDashboard.objects.filter(user=user, file_id=file_id).delete()
    return deleted > 0


def set_dashboard_pinned(user, file_id, pinned: bool) -> SavedDashboard:
    try:
        saved = SavedDashboard.objects.select_related("file").get(user=user, file_id=file_id)
    except SavedDashboard.DoesNotExist:
        raise ValueError("Dashboard is not saved")
    saved.pinned = bool(pinned)
    saved.save(update_fields=["pinned"])
    return saved


def list_saved_dashboards(user, *, query: str = ""):
    qs = (
        SavedDashboard.objects.filter(user=user)
        .select_related("file", "file__uploaded_by")
        .order_by("-pinned", "-saved_at")
    )
    q = (query or "").strip()
    if q:
        qs = qs.filter(
            Q(file__original_name__icontains=q)
            | Q(file__content_json__title__icontains=q)
            | Q(file__uploaded_by__username__icontains=q)
            | Q(file__uploaded_by__first_name__icontains=q)
            | Q(file__uploaded_by__last_name__icontains=q)
        )
    return qs


def serialize_saved_dashboard(saved: SavedDashboard) -> dict:
    file_obj = saved.file
    file_payload = serialize_file_for_ui(file_obj, user=saved.user)
    author = file_obj.uploaded_by
    title = file_payload["name"]
    subtitle = file_obj.content_json.get("subtitle") or "Dashboard interactivo"
    updated_at = file_obj.updated_at or saved.saved_at
    series = _spark_series_for_file(file_obj.id)
    tint = _spark_tint_for_file(file_obj.id)
    sparkline = _sparkline_paths(series)
    return {
        **file_payload,
        "saved": True,
        "pinned": saved.pinned,
        "saved_at": saved.saved_at.isoformat(),
        "author": _user_display_name(author),
        "initials": _user_initials(author),
        "date_label": _relative_date_label(updated_at),
        "metric": title,
        "sub": subtitle,
        "tint": tint,
        "series": series,
        "sparkline_line": sparkline["line"],
        "sparkline_area": sparkline["area"],
    }
