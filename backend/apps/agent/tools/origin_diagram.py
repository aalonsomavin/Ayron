import json
from typing import Annotated, Literal

from langchain_core.tools import InjectedToolCallId, tool

from apps.agent.tools.errors import build_tool_error_response

_ORIGIN_DIAGRAM_REGISTRY: dict[str, dict] = {}

VALID_PATTERNS = frozenset({"converge", "multi_source", "chain"})
VALID_ICONS = frozenset({"database", "sheet", "file"})
MAX_SOURCES = 4
MAX_TRANSFORMS = 3
MAX_LABEL_LEN = 40
MAX_SUBTITLE_LEN = 72
MAX_DETAIL_LEN = 200
MAX_CAPTION_LEN = 120
MAX_HINT_LEN = 160
MAX_MERGE_LABEL_LEN = 40

AGENT_INSTRUCTION_AFTER_ORIGIN_DIAGRAM = (
    "El diagrama ya está visible. Responde con una sola frase (máx. 25 palabras) "
    "que resume de dónde salieron los datos en lenguaje de negocio. "
    "No repitas nodos del diagrama ni pegues SQL."
)


def pop_origin_diagram_display(tool_call_id: str | None) -> dict | None:
    if not tool_call_id:
        return None
    return _ORIGIN_DIAGRAM_REGISTRY.pop(tool_call_id, None)


def _truncate(text: str, max_len: int) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1] + "…"


def _normalize_source(raw: dict, index: int) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"Source {index + 1} must be an object")
    label = _truncate(raw.get("label", ""), MAX_LABEL_LEN)
    if not label:
        raise ValueError(f"Source {index + 1} label cannot be empty")
    subtitle = _truncate(raw.get("subtitle", ""), MAX_SUBTITLE_LEN)
    meta = _truncate(raw.get("meta", ""), MAX_SUBTITLE_LEN)
    detail = _truncate(raw.get("detail", ""), MAX_DETAIL_LEN)
    icon = str(raw.get("icon", "")).strip().lower()
    if icon and icon not in VALID_ICONS:
        raise ValueError(f"Source {index + 1} icon must be database, sheet, or file")
    normalized = {"label": label, "subtitle": subtitle}
    if meta:
        normalized["meta"] = meta
    if icon:
        normalized["icon"] = icon
    if detail:
        normalized["detail"] = detail
    return normalized


def _normalize_merge(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("merge must be an object with label")
    label = _truncate(raw.get("label", ""), MAX_MERGE_LABEL_LEN)
    if not label:
        raise ValueError("merge.label cannot be empty")
    detail = _truncate(raw.get("detail", ""), MAX_DETAIL_LEN)
    normalized = {"label": label}
    if detail:
        normalized["detail"] = detail
    return normalized


def _normalize_transform(raw: dict, index: int) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"Transform {index + 1} must be an object")
    label = _truncate(raw.get("label", ""), MAX_LABEL_LEN)
    if not label:
        raise ValueError(f"Transform {index + 1} label cannot be empty")
    detail = _truncate(raw.get("detail", ""), MAX_DETAIL_LEN)
    normalized = {"label": label}
    if detail:
        normalized["detail"] = detail
    return normalized


def _normalize_result(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("result must be an object with label")
    label = _truncate(raw.get("label", ""), MAX_LABEL_LEN)
    if not label:
        raise ValueError("result.label cannot be empty")
    subtitle = _truncate(raw.get("subtitle", ""), MAX_SUBTITLE_LEN)
    detail = _truncate(raw.get("detail", ""), MAX_DETAIL_LEN)
    normalized = {"label": label}
    if subtitle:
        normalized["subtitle"] = subtitle
    if detail:
        normalized["detail"] = detail
    return normalized


def _expected_pattern_for_source_count(count: int) -> str:
    if count == 1:
        return "chain"
    if count == 2:
        return "converge"
    return "multi_source"


def validate_origin_diagram_input(
    pattern: str,
    sources: list[dict],
    result: dict,
    caption: str,
    hint: str,
    merge: dict | None = None,
    transforms: list[dict] | None = None,
) -> dict:
    pattern_key = str(pattern).strip().lower()
    if pattern_key not in VALID_PATTERNS:
        raise ValueError("pattern must be converge, multi_source, or chain")

    if not sources:
        raise ValueError("At least one source is required")
    if len(sources) > MAX_SOURCES:
        raise ValueError(f"Maximum {MAX_SOURCES} sources allowed")

    normalized_sources = [_normalize_source(item, idx) for idx, item in enumerate(sources)]
    expected = _expected_pattern_for_source_count(len(normalized_sources))
    if pattern_key != expected:
        raise ValueError(
            f"pattern must be {expected} for {len(normalized_sources)} source(s)"
        )

    normalized_result = _normalize_result(result)
    caption_text = _truncate(caption, MAX_CAPTION_LEN)
    hint_text = _truncate(hint, MAX_HINT_LEN)
    if not caption_text:
        raise ValueError("caption cannot be empty")
    if not hint_text:
        raise ValueError("hint cannot be empty")

    normalized_merge = None
    normalized_transforms = []

    if pattern_key in {"converge", "multi_source"}:
        normalized_merge = _normalize_merge(merge)
        if transforms:
            raise ValueError("transforms are only allowed for chain pattern")
    else:
        if merge:
            raise ValueError("merge is only allowed for converge or multi_source patterns")
        raw_transforms = transforms or []
        if len(raw_transforms) > MAX_TRANSFORMS:
            raise ValueError(f"Maximum {MAX_TRANSFORMS} transforms allowed")
        normalized_transforms = [
            _normalize_transform(item, idx) for idx, item in enumerate(raw_transforms)
        ]

    payload = {
        "ok": True,
        "pattern": pattern_key,
        "sources": normalized_sources,
        "result": normalized_result,
        "caption": caption_text,
        "hint": hint_text,
    }
    if normalized_merge:
        payload["merge"] = normalized_merge
    if normalized_transforms:
        payload["transforms"] = normalized_transforms
    return payload


def format_origin_diagram_payload(payload: dict) -> dict:
    formatted = {
        "pattern": payload.get("pattern", "chain"),
        "sources": payload.get("sources", []),
        "result": payload.get("result", {}),
        "caption": payload.get("caption", ""),
        "hint": payload.get("hint", ""),
    }
    if payload.get("merge"):
        formatted["merge"] = payload["merge"]
    if payload.get("transforms"):
        formatted["transforms"] = payload["transforms"]
    return formatted


def prepare_origin_diagram_for_render(payload: dict) -> dict:
    diagram = format_origin_diagram_payload(payload)
    for key in ("claim_id", "tool_call_id"):
        if payload.get(key):
            diagram[key] = payload[key]
    return diagram


def build_agent_tool_response(payload: dict) -> str:
    full = format_origin_diagram_payload(payload)
    return json.dumps(
        {
            "ok": True,
            "displayed_to_user": True,
            "pattern": full["pattern"],
            "source_count": len(full["sources"]),
            "agent_instruction": AGENT_INSTRUCTION_AFTER_ORIGIN_DIAGRAM,
        }
    )


@tool
def show_origin_diagram(
    pattern: Literal["converge", "multi_source", "chain"],
    sources: list[dict],
    result: dict,
    caption: str,
    hint: str,
    merge: dict | None = None,
    transforms: list[dict] | None = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Display an inline origin diagram in the chat explaining where data came from.

    Use only when the user asked about data provenance (Origen de los datos).
    Invoke this tool before writing any text response.

    **Sources = integrations**, not SQL tables. Each source node is one data connection
    (e.g. PostgreSQL · Mexar Pharma, Excel sheet, CSV file). Count distinct integrations
    to pick the pattern:
    - chain: 1 integration, with optional transform steps (filters, aggregations).
    - converge: 2 integrations merged (JOIN/cross).
    - multi_source: 3–4 distinct integrations combined.

    Use business-language labels in Spanish on visible nodes. Put tables, joins, filters,
    SUM/COUNT and other operations in merge, transforms, or node detail (click to expand)
    when they help explain the flow.

    Each source: label (integration name in business terms), subtitle (domain/dataset),
    optional meta, icon (database/sheet/file), detail (tables or scope if useful).
    merge (converge/multi_source): label and detail for the join/cross step.
    transforms (chain): up to 3 steps with label and detail.
    result: label (required), subtitle, detail for the final output node.
    caption: short flow summary (e.g. "dos integraciones → cruce → resultado").
    hint: when to use this pattern (e.g. "Cuando hay un JOIN entre dos fuentes.").

    After this call, write exactly one short closing sentence; do not repeat the diagram.
    """
    try:
        payload = validate_origin_diagram_input(
            pattern,
            sources,
            result,
            caption,
            hint,
            merge,
            transforms,
        )
    except ValueError as exc:
        return build_tool_error_response(str(exc))

    if tool_call_id:
        _ORIGIN_DIAGRAM_REGISTRY[tool_call_id] = payload
    return build_agent_tool_response(payload)
