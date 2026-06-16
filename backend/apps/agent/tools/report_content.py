from apps.agent.tools.document_style import CALLOUT_VARIANTS

MAX_SECTIONS = 20
MAX_TABLE_ROWS = 50
MAX_PARAGRAPHS_PER_SECTION = 20
MAX_BULLETS_PER_SECTION = 30
MAX_BLOCKS_PER_SECTION = 40
MAX_CALLOUTS_PER_SECTION = 8


def normalize_docx_table(table: dict) -> dict:
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
