import ast
import json

from apps.agent.tools.document_style import CALLOUT_VARIANTS
from apps.agent.tools.table_style_tokens import normalize_fill

MAX_SECTIONS = 20
MAX_TABLE_ROWS = 50
MAX_PARAGRAPHS_PER_SECTION = 20
MAX_BULLETS_PER_SECTION = 30
MAX_BLOCKS_PER_SECTION = 40
MAX_CALLOUTS_PER_SECTION = 8

VALID_CELL_TONES = frozenset({"default", "success", "danger", "warning", "muted"})
VALID_CELL_ALIGNS = frozenset({"left", "right", "center"})
VALID_ROW_STYLES = frozenset({"default", "total", "subtotal"})


def _is_corrupted_styled_row_keys(row) -> bool:
    if not isinstance(row, list) or len(row) != 2:
        return False
    return {str(item).strip().lower() for item in row} == {"style", "cells"}


def _parse_embedded_row(value) -> dict | None:
    if isinstance(value, dict):
        if "cells" in value or "row" in value:
            return value
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped.startswith("{"):
        return None
    for loader in (json.loads, ast.literal_eval):
        try:
            parsed = loader(stripped)
        except (ValueError, SyntaxError, json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict) and ("cells" in parsed or "row" in parsed):
            return parsed
    return None


def _parse_embedded_cell(value) -> dict | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped.startswith("{"):
        return None
    for loader in (json.loads, ast.literal_eval):
        try:
            parsed = loader(stripped)
        except (ValueError, SyntaxError, json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def normalize_docx_cell(cell, *, default_bold: bool = False) -> dict:
    embedded = _parse_embedded_cell(cell)
    if embedded is not None and embedded is not cell:
        return normalize_docx_cell(embedded, default_bold=default_bold)
    if isinstance(cell, dict):
        raw_value = cell.get("value", cell.get("text", ""))
        embedded_value = _parse_embedded_cell(raw_value)
        if embedded_value is not None:
            merged = dict(embedded_value)
            for key in ("tone", "align", "bold", "fill"):
                if key in cell and key not in merged:
                    merged[key] = cell[key]
            return normalize_docx_cell(merged, default_bold=default_bold)
        value = str(raw_value)
        tone = str(cell.get("tone", "default")).strip().lower()
        if tone not in VALID_CELL_TONES:
            raise ValueError(
                f"cell tone must be one of: {', '.join(sorted(VALID_CELL_TONES))}"
            )
        align = str(cell.get("align", "left")).strip().lower()
        if align not in VALID_CELL_ALIGNS:
            raise ValueError(
                f"cell align must be one of: {', '.join(sorted(VALID_CELL_ALIGNS))}"
            )
        bold = bool(cell.get("bold", default_bold))
        fill = normalize_fill(cell.get("fill", "default"))
        return {"value": value, "tone": tone, "align": align, "bold": bold, "fill": fill}
    return {
        "value": str(cell),
        "tone": "default",
        "align": "left",
        "bold": default_bold,
        "fill": "default",
    }


def normalize_docx_row(row) -> dict | None:
    embedded = _parse_embedded_row(row)
    if embedded is not None and embedded is not row:
        return normalize_docx_row(embedded)
    if _is_corrupted_styled_row_keys(row):
        return None
    if isinstance(row, dict):
        style = str(row.get("style", "default")).strip().lower()
        if style not in VALID_ROW_STYLES:
            raise ValueError(
                f"row style must be one of: {', '.join(sorted(VALID_ROW_STYLES))}"
            )
        cells = row.get("cells")
        if cells is None:
            cells = row.get("row")
        if not isinstance(cells, list):
            raise ValueError("styled row requires cells")
        default_bold = style in ("total", "subtotal")
        return {
            "style": style,
            "cells": [normalize_docx_cell(cell, default_bold=default_bold) for cell in cells],
        }
    if isinstance(row, list):
        return {
            "style": "default",
            "cells": [normalize_docx_cell(cell) for cell in row],
        }
    raise ValueError("each table row must be a list or an object with cells")


def normalize_docx_table(table: dict) -> dict:
    if not isinstance(table, dict):
        raise ValueError("table must be an object")
    headers = table.get("headers") or []
    rows = table.get("rows") or []
    if not headers:
        raise ValueError("table requires headers")
    if len(rows) > MAX_TABLE_ROWS:
        raise ValueError(f"table rows exceeds maximum of {MAX_TABLE_ROWS}")
    normalized_rows = []
    for row in rows:
        normalized = normalize_docx_row(row)
        if normalized is not None:
            normalized_rows.append(normalized)
    result = {
        "headers": [str(h) for h in headers],
        "rows": normalized_rows,
    }
    caption = str(table.get("caption", "")).strip()
    if caption:
        result["caption"] = caption
    return result


def normalize_common_block(block: dict, callout_count: int) -> tuple[dict | None, int]:
    block_type = block.get("type")
    if block_type == "paragraph":
        text = str(block.get("text", "")).strip()
        if text:
            return {"type": "paragraph", "text": text}, callout_count
        return None, callout_count
    if block_type == "bullets":
        items = block.get("items") or []
        if not isinstance(items, list):
            raise ValueError("bullets items must be a list")
        if len(items) > MAX_BULLETS_PER_SECTION:
            raise ValueError(f"bullets exceeds maximum of {MAX_BULLETS_PER_SECTION}")
        clean_items = [str(item) for item in items if str(item).strip()]
        if clean_items:
            return {"type": "bullets", "items": clean_items}, callout_count
        return None, callout_count
    if block_type == "separator":
        return {"type": "separator"}, callout_count
    if block_type == "callout":
        callout_count += 1
        if callout_count > MAX_CALLOUTS_PER_SECTION:
            raise ValueError(f"callouts exceeds maximum of {MAX_CALLOUTS_PER_SECTION}")
        variant = str(block.get("variant", "info")).strip().lower()
        if variant not in CALLOUT_VARIANTS:
            raise ValueError(f"callout variant must be one of: {', '.join(CALLOUT_VARIANTS)}")
        text = str(block.get("text", "")).strip()
        if not text:
            raise ValueError("callout requires text")
        return (
            {
                "type": "callout",
                "variant": variant,
                "title": str(block.get("title", "")).strip(),
                "text": text,
            },
            callout_count,
        )
    return None, callout_count


def normalize_docx_blocks(section: dict) -> list[dict]:
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
            if block_type == "table":
                normalized.append({"type": "table", **normalize_docx_table(block)})
                continue
            if block_type not in ("paragraph", "bullets", "separator", "callout"):
                raise ValueError(
                    "block type must be paragraph, bullets, table, separator, or callout"
                )
            normalized_block, callout_count = normalize_common_block(block, callout_count)
            if normalized_block:
                normalized.append(normalized_block)
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
        blocks.append({"type": "table", **normalize_docx_table(table)})
    return blocks


def validate_docx_content_json(
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
        blocks = normalize_docx_blocks(section)
        normalized_sections.append({"heading": heading, "blocks": blocks})

    return {
        "format": "docx",
        "title": str(title).strip(),
        "subtitle": str(subtitle or "").strip(),
        "sections": normalized_sections,
    }


def revalidate_docx_content_json(content_json: dict) -> dict:
    return validate_docx_content_json(
        content_json.get("title", ""),
        content_json.get("subtitle", ""),
        content_json.get("sections", []),
    )
