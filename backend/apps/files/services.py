from __future__ import annotations

import html
from io import BytesIO

from django.core.files.base import ContentFile

from apps.chat.models import Conversation
from apps.files.models import DOCX_MIME, HTML_MIME, File


def _section_count(content_json: dict) -> int:
    return len(content_json.get("sections") or [])


def _file_meta(content_json: dict) -> str:
    format_key = content_json.get("format", "docx")
    if format_key == "html":
        return "Report · HTML"
    sections = _section_count(content_json)
    page_word = "sección" if sections == 1 else "secciones"
    return f"Document · {sections} {page_word}"


def _file_ext(content_json: dict, mime_type: str) -> str:
    format_key = content_json.get("format")
    if format_key == "html" or mime_type == HTML_MIME:
        return "HTML"
    return "DOCX"


def serialize_file_for_ui(file_obj: File) -> dict:
    format_key = file_obj.format_key
    payload = {
        "file_id": str(file_obj.id),
        "name": file_obj.original_name,
        "ext": _file_ext(file_obj.content_json, file_obj.mime_type),
        "format": format_key,
        "mime": file_obj.mime_type,
        "meta": _file_meta(file_obj.content_json),
        "version": file_obj.version,
        "download_url": f"/files/{file_obj.id}/download/",
        "preview_url": f"/files/{file_obj.id}/preview/",
    }
    if format_key == "html":
        payload["download_pdf_url"] = f"/files/{file_obj.id}/download/pdf/"
    return payload


def serialize_file_for_agent(file_obj: File) -> dict:
    return {
        "file_id": str(file_obj.id),
        "name": file_obj.original_name,
        "format": file_obj.format_key,
        "version": file_obj.version,
        "updated_at": file_obj.updated_at.isoformat(),
        "summary": file_obj.content_json.get("title", ""),
    }


def get_agent_file_index(conversation: Conversation) -> list[dict]:
    files = File.objects.filter(conversation=conversation).order_by("created_at")
    return [serialize_file_for_agent(file_obj) for file_obj in files]


def format_agent_file_index_block(conversation: Conversation) -> str:
    entries = get_agent_file_index(conversation)
    if not entries:
        return ""
    lines = ["## Archivos de esta conversación", ""]
    for entry in entries:
        format_label = entry.get("format", "docx").upper()
        lines.append(
            f"- file_id={entry['file_id']} · {entry['name']} · {format_label} · "
            f"v{entry['version']} · {entry['summary'] or 'sin título'}"
        )
    lines.append("")
    return "\n".join(lines)


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
    file_obj = File(
        uploaded_by=user,
        conversation=conversation,
        original_name=original_name,
        mime_type=mime_type,
        content_json=content_json,
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
