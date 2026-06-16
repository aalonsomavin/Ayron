import json
import re
from datetime import date
from io import BytesIO
from typing import Annotated

from docx import Document
from langchain_core.tools import InjectedToolCallId, tool

from apps.agent.context import get_agent_conversation, get_agent_user
from apps.agent.tools.document_style import (
    CALLOUT_VARIANTS,
    PAGE_HEIGHT_IN,
    PAGE_MARGIN_IN,
    PAGE_WIDTH_IN,
    add_body_paragraph,
    add_bullet_item,
    add_callout,
    add_document_header,
    add_section_heading,
    add_separator,
    add_styled_table,
    configure_document_footer,
    configure_document_header,
    configure_document_styles,
    footer_attribution_text,
    preview_px,
)
from apps.files.services import (
    get_file_for_conversation,
    save_generated_file,
    serialize_file_for_agent,
    serialize_file_for_ui,
    update_generated_file,
)
from apps.files.services import escape_preview_text as esc

_DOCUMENT_DISPLAY_REGISTRY: dict[str, dict] = {}

MAX_SECTIONS = 20
MAX_TABLE_ROWS = 50
MAX_PARAGRAPHS_PER_SECTION = 20
MAX_BULLETS_PER_SECTION = 30
MAX_BLOCKS_PER_SECTION = 40
MAX_CALLOUTS_PER_SECTION = 8

AGENT_INSTRUCTION_AFTER_DOCUMENT = (
    "El documento ya está visible en el chat del usuario. "
    "NO repitas el contenido del informe en tu siguiente mensaje. "
    "Solo añade una frase breve si aporta contexto, o termina sin texto."
)


def pop_document_display(tool_call_id: str | None) -> dict | None:
    if not tool_call_id:
        return None
    return _DOCUMENT_DISPLAY_REGISTRY.pop(tool_call_id, None)


def _sanitize_filename(name: str, fallback: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name).strip()
    if not cleaned:
        cleaned = fallback
    if not cleaned.lower().endswith(".docx"):
        cleaned = f"{cleaned}.docx"
    return cleaned[:200]


def _normalize_table(table: dict) -> dict:
    if not isinstance(table, dict):
        raise ValueError("table must be an object")
    headers = table.get("headers") or []
    rows = table.get("rows") or []
    if not headers:
        raise ValueError("table requires headers")
    if len(rows) > MAX_TABLE_ROWS:
        raise ValueError(f"table rows exceeds maximum of {MAX_TABLE_ROWS}")
    return {
        "headers": [str(h) for h in headers],
        "rows": [[str(cell) for cell in row] for row in rows],
    }


def _normalize_blocks(section: dict) -> list[dict]:
    raw_blocks = section.get("blocks")
    if raw_blocks is not None:
        if not isinstance(raw_blocks, list):
            raise ValueError("blocks must be a list")
        if len(raw_blocks) > MAX_BLOCKS_PER_SECTION:
            raise ValueError(f"blocks exceeds maximum of {MAX_BLOCKS_PER_SECTION}")
        normalized = []
        callout_count = 0
        for block in raw_blocks:
            if not isinstance(block, dict):
                raise ValueError("each block must be an object")
            block_type = block.get("type")
            if block_type == "paragraph":
                text = str(block.get("text", "")).strip()
                if text:
                    normalized.append({"type": "paragraph", "text": text})
            elif block_type == "bullets":
                items = block.get("items") or []
                if not isinstance(items, list):
                    raise ValueError("bullets items must be a list")
                if len(items) > MAX_BULLETS_PER_SECTION:
                    raise ValueError(f"bullets exceeds maximum of {MAX_BULLETS_PER_SECTION}")
                clean_items = [str(item) for item in items if str(item).strip()]
                if clean_items:
                    normalized.append({"type": "bullets", "items": clean_items})
            elif block_type == "table":
                normalized.append({"type": "table", **_normalize_table(block)})
            elif block_type == "separator":
                normalized.append({"type": "separator"})
            elif block_type == "callout":
                callout_count += 1
                if callout_count > MAX_CALLOUTS_PER_SECTION:
                    raise ValueError(f"callouts exceeds maximum of {MAX_CALLOUTS_PER_SECTION}")
                variant = str(block.get("variant", "info")).strip().lower()
                if variant not in CALLOUT_VARIANTS:
                    raise ValueError(f"callout variant must be one of: {', '.join(CALLOUT_VARIANTS)}")
                text = str(block.get("text", "")).strip()
                if not text:
                    raise ValueError("callout requires text")
                normalized.append(
                    {
                        "type": "callout",
                        "variant": variant,
                        "title": str(block.get("title", "")).strip(),
                        "text": text,
                    }
                )
            else:
                raise ValueError(
                    "block type must be paragraph, bullets, table, separator, or callout"
                )
        return normalized

    blocks = []
    paragraphs = section.get("paragraphs") or []
    bullets = section.get("bullets") or []
    table = section.get("table")

    if not isinstance(paragraphs, list):
        raise ValueError("paragraphs must be a list")
    if not isinstance(bullets, list):
        raise ValueError("bullets must be a list")
    if len(paragraphs) > MAX_PARAGRAPHS_PER_SECTION:
        raise ValueError(f"paragraphs exceeds maximum of {MAX_PARAGRAPHS_PER_SECTION}")
    if len(bullets) > MAX_BULLETS_PER_SECTION:
        raise ValueError(f"bullets exceeds maximum of {MAX_BULLETS_PER_SECTION}")

    for paragraph in paragraphs:
        text = str(paragraph).strip()
        if text:
            blocks.append({"type": "paragraph", "text": text})
    if bullets:
        blocks.append({"type": "bullets", "items": [str(b) for b in bullets]})
    if table is not None:
        blocks.append({"type": "table", **_normalize_table(table)})
    return blocks


def validate_content_json(
    title: str,
    subtitle: str,
    sections: list,
) -> dict:
    if not title or not str(title).strip():
        raise ValueError("title is required")
    if not isinstance(sections, list) or not sections:
        raise ValueError("sections must be a non-empty list")
    if len(sections) > MAX_SECTIONS:
        raise ValueError(f"sections exceeds maximum of {MAX_SECTIONS}")

    normalized_sections = []
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError("each section must be an object")
        heading = str(section.get("heading", "")).strip()
        if not heading:
            raise ValueError("each section requires a heading")
        blocks = _normalize_blocks(section)
        normalized_sections.append({"heading": heading, "blocks": blocks})

    return {
        "title": str(title).strip(),
        "subtitle": str(subtitle or "").strip(),
        "sections": normalized_sections,
    }


def _render_block_docx(doc: Document, block: dict) -> None:
    block_type = block["type"]
    if block_type == "paragraph":
        add_body_paragraph(doc, block["text"])
    elif block_type == "bullets":
        for item in block["items"]:
            add_bullet_item(doc, item)
    elif block_type == "table":
        add_styled_table(doc, block["headers"], block["rows"])
    elif block_type == "separator":
        add_separator(doc)
    elif block_type == "callout":
        add_callout(
            doc,
            variant=block["variant"],
            title=block.get("title", ""),
            text=block["text"],
        )


def build_docx(content_json: dict) -> bytes:
    doc = Document()
    generated_on = date.today()
    configure_document_styles(doc)
    configure_document_header(doc)
    configure_document_footer(doc, generated_on)

    add_document_header(doc, content_json.get("title", ""), content_json.get("subtitle", ""))

    for section in content_json.get("sections", []):
        add_section_heading(doc, section.get("heading", ""))
        for block in section.get("blocks", []):
            _render_block_docx(doc, block)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _render_table_html(table_data: dict) -> str:
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])
    if not headers:
        return ""
    head_cells = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body_rows = []
    for row_idx, row in enumerate(rows):
        row_class = "ay-doc-preview__table-row--alt" if row_idx % 2 else ""
        padded = list(row[: len(headers)])
        while len(padded) < len(headers):
            padded.append("")
        cells = "".join(f"<td>{esc(cell)}</td>" for cell in padded)
        cls_attr = f' class="{row_class}"' if row_class else ""
        body_rows.append(f"<tr{cls_attr}>{cells}</tr>")
    return (
        f'<table class="ay-doc-preview__table"><thead><tr>{head_cells}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )


def _render_callout_html(block: dict) -> str:
    variant = block.get("variant", "info")
    title = esc(block.get("title") or CALLOUT_VARIANTS.get(variant, {}).get("label", "Nota"))
    text = esc(block.get("text", ""))
    return (
        f'<div class="ay-doc-preview__callout ay-doc-preview__callout--{esc(variant)}">'
        f'<div class="ay-doc-preview__callout-title">{title}</div>'
        f'<div class="ay-doc-preview__callout-text">{text}</div>'
        f"</div>"
    )


def _render_document_header_html(title: str, subtitle: str) -> str:
    parts = [
        '<header class="ay-doc-preview__doc-header">',
        f'<h1 class="ay-doc-preview__doc-header-title">{title}</h1>',
    ]
    if subtitle:
        parts.append(f'<p class="ay-doc-preview__doc-header-subtitle">{subtitle}</p>')
    parts.append("</header>")
    parts.append('<div class="ay-doc-preview__doc-header-rule" role="presentation"></div>')
    return "".join(parts)


def _render_block_html(block: dict) -> str:
    block_type = block["type"]
    if block_type == "paragraph":
        return f'<p class="ay-doc-preview__p">{esc(block["text"])}</p>'
    if block_type == "bullets":
        items = "".join(f"<li>{esc(item)}</li>" for item in block["items"])
        return f'<ul class="ay-doc-preview__ul">{items}</ul>'
    if block_type == "table":
        return _render_table_html(block)
    if block_type == "separator":
        return '<div class="ay-doc-preview__separator" role="presentation"></div>'
    if block_type == "callout":
        return _render_callout_html(block)
    return ""


def build_preview_html(content_json: dict) -> str:
    title = esc(content_json.get("title", ""))
    subtitle = esc(content_json.get("subtitle", ""))
    generated_on = date.today()
    parts = [
        (
            '<div class="ay-doc-preview"'
            f' data-page-width-px="{preview_px(PAGE_WIDTH_IN)}"'
            f' data-page-height-px="{preview_px(PAGE_HEIGHT_IN)}"'
            f' data-page-margin-px="{preview_px(PAGE_MARGIN_IN)}"'
            f' data-footer-attribution="{esc(footer_attribution_text(generated_on))}">'
        ),
        '<div class="ay-doc-preview__source">',
        _render_document_header_html(title, subtitle),
    ]

    for section in content_json.get("sections", []):
        heading = esc(section.get("heading", ""))
        parts.append(f'<h2 class="ay-doc-preview__heading">{heading}</h2>')
        for block in section.get("blocks", []):
            parts.append(_render_block_html(block))

    parts.extend(["</div>", '<div class="ay-doc-preview__pages"></div>', "</div>"])
    return "".join(parts)


def preview_html_for_file(content_json: dict | None, preview_html: str) -> str:
    if content_json and content_json.get("sections") is not None:
        return build_preview_html(content_json)
    return preview_html or ""


def _merge_content_json(existing: dict, title, subtitle, sections) -> dict:
    merged = dict(existing)
    if title is not None:
        merged["title"] = str(title).strip()
    if subtitle is not None:
        merged["subtitle"] = str(subtitle).strip()
    if sections is not None:
        merged["sections"] = sections
    return validate_content_json(
        merged.get("title", ""),
        merged.get("subtitle", ""),
        merged.get("sections", []),
    )


def _build_agent_tool_response(file_obj, action: str) -> str:
    return json.dumps(
        {
            "ok": True,
            "action": action,
            "file_id": str(file_obj.id),
            "name": file_obj.original_name,
            "version": file_obj.version,
            "agent_instruction": AGENT_INSTRUCTION_AFTER_DOCUMENT,
        }
    )


def _register_display(tool_call_id: str, file_obj, updated: bool = False) -> None:
    payload = serialize_file_for_ui(file_obj)
    payload["updated"] = updated
    _DOCUMENT_DISPLAY_REGISTRY[tool_call_id] = payload


@tool
def create_document(
    title: str,
    sections: list[dict],
    subtitle: str = "",
    filename: str = "",
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Create a Word document (.docx) for the user in the chat.

    Use when the user asks for a report, memo, or exportable written document.
    Set `title` to a descriptive document name for the header (not a generic label).
    Use `subtitle` for one line of context under the title (period, scope, audience).
    Each section supports blocks: paragraph, bullets, table, separator, callout.
    Callout variants: info, success, warning, danger.
    The document appears in the chat; do not repeat its content in your text response.

    To modify an existing document later, use update_document with the same file_id.
    """
    conversation = get_agent_conversation()
    user = get_agent_user()
    if conversation is None or user is None:
        return json.dumps({"ok": False, "error": "No conversation context"})

    try:
        content_json = validate_content_json(title, subtitle, sections)
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})

    original_name = _sanitize_filename(filename, content_json["title"])
    docx_bytes = build_docx(content_json)
    preview_html = build_preview_html(content_json)

    file_obj = save_generated_file(
        conversation=conversation,
        user=user,
        original_name=original_name,
        content_json=content_json,
        docx_bytes=docx_bytes,
        preview_html=preview_html,
    )
    _register_display(tool_call_id, file_obj, updated=False)
    return _build_agent_tool_response(file_obj, "created")


@tool
def list_conversation_files() -> str:
    """List Word documents generated in the current conversation.

    Returns file_id, name, version, and summary for each document.
    """
    conversation = get_agent_conversation()
    if conversation is None:
        return json.dumps({"ok": False, "error": "No conversation context"})

    from apps.files.services import get_agent_file_index

    files = get_agent_file_index(conversation)
    return json.dumps({"ok": True, "files": files})


@tool
def get_document(file_id: str) -> str:
    """Read the full structured content of a document by file_id.

    Call this before update_document when you need the current sections.
    """
    conversation = get_agent_conversation()
    if conversation is None:
        return json.dumps({"ok": False, "error": "No conversation context"})

    file_obj = get_file_for_conversation(file_id, conversation)
    if file_obj is None:
        return json.dumps({"ok": False, "error": "Document not found in this conversation"})

    return json.dumps(
        {
            "ok": True,
            **serialize_file_for_agent(file_obj),
            "content_json": file_obj.content_json,
        }
    )


@tool
def update_document(
    file_id: str,
    title: str | None = None,
    subtitle: str | None = None,
    sections: list[dict] | None = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Update an existing Word document by file_id.

    Provide only the fields you want to change. sections replaces all sections when provided.
    Use a descriptive `title` for the document header when updating the document name.
    """
    conversation = get_agent_conversation()
    if conversation is None:
        return json.dumps({"ok": False, "error": "No conversation context"})

    file_obj = get_file_for_conversation(file_id, conversation)
    if file_obj is None:
        return json.dumps({"ok": False, "error": "Document not found in this conversation"})

    try:
        content_json = _merge_content_json(file_obj.content_json, title, subtitle, sections)
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})

    docx_bytes = build_docx(content_json)
    preview_html = build_preview_html(content_json)
    file_obj = update_generated_file(
        file_obj=file_obj,
        content_json=content_json,
        docx_bytes=docx_bytes,
        preview_html=preview_html,
    )
    _register_display(tool_call_id, file_obj, updated=True)
    return _build_agent_tool_response(file_obj, "updated")
