import json
from typing import Annotated, Literal

from langchain_core.tools import InjectedToolCallId, tool

_CHART_DISPLAY_REGISTRY: dict[str, dict] = {}

VALID_CHART_TYPES = frozenset({"bar", "line", "pie"})
VALID_VALUE_FORMATS = frozenset({"number", "currency", "percent"})
MAX_LABELS = 25
MAX_SERIES = 8
MAX_TITLE_LEN = 80
MAX_CAPTION_LEN = 200

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
    return chart


@tool
def show_chart(
    chart_type: Literal["bar", "line", "pie"],
    labels: list[str],
    series: list[dict],
    title: str = "",
    caption: str = "",
    value_format: Literal["number", "currency", "percent"] = "number",
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> str:
    """Display an inline chart in the chat for the user.

    Use when visualizing aggregated data: bar for categories, line for trends over time,
    pie for parts of a whole (at most 8 segments). At most 25 labels.

    The UI renders the chart for the user. Your tool response does not need to repeat
    data points — after this call, write at most a brief interpretation or stop.

    Pass numeric values (not pre-formatted strings). Use Spanish labels.
    For pie charts, pass exactly one series.
    """
    try:
        payload = validate_chart_input(
            chart_type,
            labels,
            series,
            title,
            caption,
            value_format,
        )
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    if tool_call_id:
        _CHART_DISPLAY_REGISTRY[tool_call_id] = payload
    return build_agent_tool_response(payload)
