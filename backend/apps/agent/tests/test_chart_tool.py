import json

import pytest

from apps.agent.tools.chart import (
    MAX_LABELS,
    MAX_SERIES,
    pop_chart_display,
    prepare_chart_for_render,
    show_chart,
    validate_chart_input,
)


def invoke_show_chart(**kwargs):
    result = show_chart.invoke(
        {
            "type": "tool_call",
            "name": "show_chart",
            "id": "call_test",
            "args": kwargs,
        }
    )
    return result.content if hasattr(result, "content") else result


class TestValidateChartInput:
    def test_valid_bar_chart(self):
        payload = validate_chart_input(
            chart_type="bar",
            labels=["EMEA", "APAC"],
            series=[{"name": "Ingresos", "values": [486200, 248910]}],
            title="Por región",
            value_format="currency",
        )
        assert payload["ok"] is True
        assert payload["chart_type"] == "bar"
        assert payload["point_count"] == 2

    def test_rejects_invalid_chart_type(self):
        with pytest.raises(ValueError, match="chart_type must be"):
            validate_chart_input(
                chart_type="scatter",
                labels=["A"],
                series=[{"name": "S", "values": [1]}],
            )

    def test_rejects_too_many_labels(self):
        labels = [f"L{i}" for i in range(MAX_LABELS + 1)]
        with pytest.raises(ValueError, match=f"Maximum {MAX_LABELS} labels"):
            validate_chart_input(
                chart_type="bar",
                labels=labels,
                series=[{"name": "S", "values": [1] * (MAX_LABELS + 1)}],
            )

    def test_rejects_pie_with_multiple_series(self):
        with pytest.raises(ValueError, match="only one series"):
            validate_chart_input(
                chart_type="pie",
                labels=["A", "B"],
                series=[
                    {"name": "S1", "values": [1, 2]},
                    {"name": "S2", "values": [3, 4]},
                ],
            )


class TestPrepareChartForRender:
    def test_builds_datasets_for_bar(self):
        chart = prepare_chart_for_render(
            validate_chart_input(
                chart_type="bar",
                labels=["EMEA", "APAC"],
                series=[{"name": "Ingresos", "values": [100, 200]}],
            )
        )
        assert chart["datasets"] == [
            {"label": "Ingresos", "data": [100.0, 200.0], "color_index": 0}
        ]

    def test_builds_color_indices_for_pie(self):
        chart = prepare_chart_for_render(
            validate_chart_input(
                chart_type="pie",
                labels=["A", "B", "C"],
                series=[{"name": "Total", "values": [50, 30, 20]}],
            )
        )
        assert chart["datasets"][0]["color_indices"] == [0, 1, 2]
        assert chart["datasets"][0]["data"] == [50.0, 30.0, 20.0]


class TestShowChartTool:
    def test_success_response_omits_series_from_agent_payload(self):
        result = json.loads(
            invoke_show_chart(
                chart_type="bar",
                labels=["EMEA"],
                series=[{"name": "Ingresos", "values": [100]}],
            )
        )
        assert result["ok"] is True
        assert result["displayed_to_user"] is True
        assert "series" not in result
        assert "agent_instruction" in result

    def test_stores_payload_for_stream_resolution(self):
        invoke_show_chart(
            chart_type="bar",
            labels=["EMEA"],
            series=[{"name": "Ingresos", "values": [100]}],
        )
        payload = pop_chart_display("call_test")
        assert payload is not None
        assert payload["labels"] == ["EMEA"]
