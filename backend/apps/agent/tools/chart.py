import json
import uuid
from html import escape
from typing import Annotated, Literal

from django.utils.html import json_script
from langchain_core.tools import InjectedToolCallId, tool

from apps.agent.context import get_agent_conversation, get_agent_message
from apps.agent.tools.errors import build_tool_error_response
from apps.provenance.claims import create_inline_claim, normalize_inline_source_refs
from apps.provenance.models import DataClaim

_CHART_DISPLAY_REGISTRY: dict[str, dict] = {}

VALID_CHART_TYPES = frozenset({"bar", "line", "pie"})
VALID_VALUE_FORMATS = frozenset({"number", "currency", "percent"})
MAX_LABELS = 25
MAX_SERIES = 8
MAX_TITLE_LEN = 80
MAX_CAPTION_LEN = 200
MAX_CURRENCY_LABEL_LEN = 60

AGENT_INSTRUCTION_AFTER_CHART = (
    "El gráfico ya está visible en el chat del usuario. "
    "NO repitas valores, etiquetas ni series en tu siguiente mensaje. "
    "No uses listas ni tablas markdown con los mismos datos. "
    "Solo añade una o dos frases de interpretación si aportan contexto, "
    "o termina sin texto."
)


def pop_chart_display(tool_call_id: str | None) -> dict | None:
    if not tool_call_id:
        return None
    return _CHART_DISPLAY_REGISTRY.pop(tool_call_id, None)


def _coerce_number(value) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not allowed")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            raise ValueError("Empty numeric value")
        return float(text)
    raise ValueError(f"Invalid numeric value: {value!r}")


def _normalize_series(raw_series: list, label_count: int, chart_type: str) -> list[dict]:
    if not raw_series:
        raise ValueError("At least one series is required")

    if chart_type == "pie" and len(raw_series) > 1:
        raise ValueError("Pie charts support only one series")

    if len(raw_series) > MAX_SERIES:
        raise ValueError(f"Maximum {MAX_SERIES} series allowed")

    normalized = []
    for series_idx, item in enumerate(raw_series):
        if not isinstance(item, dict):
            raise ValueError(f"Series {series_idx + 1} must be an object with name and values")
        name = str(item.get("name", "")).strip()
        if not name:
            raise ValueError(f"Series {series_idx + 1} name cannot be empty")
        values = item.get("values")
        if not isinstance(values, list):
            raise ValueError(f"Series {series_idx + 1} values must be a list")
        if len(values) != label_count:
            raise ValueError(
                f"Series {series_idx + 1} has {len(values)} values, expected {label_count}"
            )
        numeric_values = []
        for value_idx, value in enumerate(values):
            try:
                numeric_values.append(_coerce_number(value))
            except ValueError as exc:
                raise ValueError(
                    f"Series {series_idx + 1}, value {value_idx + 1}: {exc}"
                ) from exc
        normalized.append({"name": name, "values": numeric_values})
    return normalized


def validate_chart_input(
    chart_type: str,
    labels: list[str],
    series: list[dict],
    title: str = "",
    caption: str = "",
    value_format: str = "number",
    currency_label: str = "",
) -> dict:
    chart_key = str(chart_type).strip().lower()
    if chart_key not in VALID_CHART_TYPES:
        raise ValueError("chart_type must be bar, line, or pie")

    format_key = str(value_format).strip().lower()
    if format_key not in VALID_VALUE_FORMATS:
        raise ValueError("value_format must be number, currency, or percent")

    if not labels:
        raise ValueError("At least one label is required")
    if len(labels) > MAX_LABELS:
        raise ValueError(f"Maximum {MAX_LABELS} labels allowed")

    normalized_labels = [str(label).strip() for label in labels]
    if any(not label for label in normalized_labels):
        raise ValueError("Labels cannot be empty")

    if len(title) > MAX_TITLE_LEN:
        raise ValueError(f"Title must be at most {MAX_TITLE_LEN} characters")
    if len(caption) > MAX_CAPTION_LEN:
        raise ValueError(f"Caption must be at most {MAX_CAPTION_LEN} characters")

    currency_label_text = str(currency_label).strip()
    if len(currency_label_text) > MAX_CURRENCY_LABEL_LEN:
        raise ValueError(
            f"currency_label must be at most {MAX_CURRENCY_LABEL_LEN} characters"
        )
    if format_key == "currency" and not currency_label_text:
        raise ValueError("currency_label is required when value_format is currency")

    normalized_series = _normalize_series(series, len(normalized_labels), chart_key)

    all_values = [value for item in normalized_series for value in item["values"]]
    if chart_key == "pie" and min(all_values) < 0:
        raise ValueError("Pie charts require non-negative values")

    return {
        "ok": True,
        "chart_type": chart_key,
        "title": title.strip(),
        "caption": caption.strip(),
        "labels": normalized_labels,
        "series": normalized_series,
        "value_format": format_key,
        "currency_label": currency_label_text,
        "point_count": len(normalized_labels),
    }


def format_chart_payload(payload: dict) -> dict:
    return {
        "chart_type": payload.get("chart_type", "bar"),
        "title": payload.get("title", ""),
        "caption": payload.get("caption", ""),
        "labels": payload.get("labels", []),
        "series": payload.get("series", []),
        "value_format": payload.get("value_format", "number"),
        "currency_label": payload.get("currency_label", ""),
        "point_count": payload.get("point_count", len(payload.get("labels", []))),
    }


def build_agent_tool_response(payload: dict) -> str:
    full = format_chart_payload(payload)
    return json.dumps(
        {
            "ok": True,
            "displayed_to_user": True,
            "chart_type": full["chart_type"],
            "point_count": full["point_count"],
            "agent_instruction": AGENT_INSTRUCTION_AFTER_CHART,
        }
    )


def render_inline_chart_html(payload: dict, chart_id: str | None = None) -> str:
    chart = prepare_chart_for_render(format_chart_payload(payload))
    cid = chart_id or f"chart-{uuid.uuid4().hex[:10]}"
    parts = [
        f'<div class="ay-chart" data-chart-id="{escape(cid, quote=True)}">',
        json_script(chart, cid),
        '<div class="ay-chart__card">',
    ]
    if chart.get("title"):
        parts.append(f'<div class="ay-chart__title">{escape(chart["title"])}</div>')
    parts.append(
        '<div class="ay-chart__plot"><canvas class="ay-chart__canvas"></canvas></div>'
    )
    if chart.get("caption"):
        parts.append(f'<div class="ay-chart__caption">{escape(chart["caption"])}</div>')
    parts.extend(["</div>", "</div>"])
    return "".join(parts)


def prepare_chart_for_render(payload: dict) -> dict:
    chart = format_chart_payload(payload)
    chart_type = chart["chart_type"]
    datasets = []

    if chart_type == "pie" and chart["series"]:
        series = chart["series"][0]
        datasets.append(
            {
                "label": series["name"],
                "data": series["values"],
                "color_indices": list(range(len(chart["labels"]))),
            }
        )
    else:
        for series_idx, series in enumerate(chart["series"]):
            datasets.append(
                {
                    "label": series["name"],
                    "data": series["values"],
                    "color_index": series_idx % MAX_SERIES,
                }
            )

    chart["datasets"] = datasets
    for key in ("claim_id", "tool_call_id"):
        if payload.get(key):
            chart[key] = payload[key]
    return chart


@tool
def show_chart(
    chart_type: Literal["bar", "line", "pie"],
    labels: list[str],
    series: list[dict],
    title: str = "",
    caption: str = "",
    value_format: Literal["number", "currency", "percent"] = "number",
    currency_label: str = "",
    source_refs: list[str] | None = None,
    tool_call_ids: list[str] | None = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Display an inline chart in the chat for the user.

    Use when visualizing aggregated data: bar for categories, line for trends over time,
    pie for parts of a whole (at most 8 segments). At most 25 labels.

    The UI renders the chart for the user. Your tool response does not need to repeat
    data points — after this call, write at most a brief interpretation or stop.

    Pass numeric values (not pre-formatted strings). Use Spanish labels.
    For pie charts, pass exactly one series.
    When value_format is currency, pass currency_label (e.g. "pesos mexicanos");
    values render with $ and the label names the currency on the axis.

    Optional source_refs links this chart to prior SQL queries for provenance.
    Use the source_ref value returned by each successful run_sql_query (e.g. sql_1).
    tool_call_ids is accepted for backward compatibility.
    """
    try:
        payload = validate_chart_input(
            chart_type,
            labels,
            series,
            title,
            caption,
            value_format,
            currency_label,
        )
    except ValueError as exc:
        return build_tool_error_response(str(exc))

    resolved_source_refs = normalize_inline_source_refs(source_refs, tool_call_ids)
    if resolved_source_refs:
        conversation = get_agent_conversation()
        message = get_agent_message()
        if conversation is None:
            return build_tool_error_response("No conversation context")
        try:
            claim = create_inline_claim(
                conversation,
                message,
                DataClaim.Surface.CHAT_CHART,
                tool_call_id,
                resolved_source_refs,
                label=payload.get("title") or payload.get("caption") or "Gráfico",
            )
            payload["claim_id"] = str(claim.id)
        except ValueError as exc:
            return build_tool_error_response(str(exc))

    if tool_call_id:
        _CHART_DISPLAY_REGISTRY[tool_call_id] = payload
    return build_agent_tool_response(payload)
