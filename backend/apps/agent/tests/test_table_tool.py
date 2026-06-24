import json

import pytest

from apps.agent.tools.table import (
    MAX_DISPLAY_COLS,
    MAX_DISPLAY_ROWS,
    build_grid_template_columns,
    detect_numeric_columns,
    infer_column_widths,
    pop_table_display,
    prepare_table_for_render,
    show_data_table,
    validate_table_input,
)


def invoke_show_data_table(**kwargs):
    result = show_data_table.invoke(
        {
            "type": "tool_call",
            "name": "show_data_table",
            "id": "call_test",
            "args": kwargs,
        }
    )
    return result.content if hasattr(result, "content") else result


class TestValidateTableInput:
    def test_valid_table(self):
        payload = validate_table_input(
            columns=["Región", "Total"],
            rows=[["EMEA", "€412,100"], ["APAC", "€298,400"]],
            caption="Mayo 2026",
        )
        assert payload["ok"] is True
        assert payload["caption"] == "Mayo 2026"
        assert payload["row_count"] == 2
        assert payload["rows"][0] == ["EMEA", "€412,100"]

    def test_normalizes_none_cells(self):
        payload = validate_table_input(
            columns=["Name", "Value"],
            rows=[["Alpha", None]],
        )
        assert payload["rows"][0] == ["Alpha", "—"]

    def test_rejects_empty_columns(self):
        with pytest.raises(ValueError, match="At least one column"):
            validate_table_input(columns=[], rows=[])

    def test_rejects_too_many_rows(self):
        rows = [["x"] for _ in range(MAX_DISPLAY_ROWS + 1)]
        with pytest.raises(ValueError, match=f"Maximum {MAX_DISPLAY_ROWS} rows"):
            validate_table_input(columns=["Col"], rows=rows)

    def test_rejects_too_many_columns(self):
        columns = [f"Col {i}" for i in range(MAX_DISPLAY_COLS + 1)]
        with pytest.raises(ValueError, match=f"Maximum {MAX_DISPLAY_COLS} columns"):
            validate_table_input(columns=columns, rows=[])

    def test_rejects_row_length_mismatch(self):
        with pytest.raises(ValueError, match="Row 1 has 1 cells"):
            validate_table_input(columns=["A", "B"], rows=[["only one"]])

    def test_truncates_long_cells(self):
        payload = validate_table_input(
            columns=["Text"],
            rows=[["x" * 250]],
        )
        assert payload["rows"][0][0].endswith("…")
        assert len(payload["rows"][0][0]) == 200


class TestDetectNumericColumns:
    def test_detects_numeric_column(self):
        rows = [["EMEA", "412100"], ["APAC", "298400"]]
        assert detect_numeric_columns(rows) == [False, True]

    def test_detects_formatted_numbers(self):
        rows = [["Product", "$284,200"], ["Other", "+14.2%"]]
        assert detect_numeric_columns(rows) == [False, True]


class TestPrepareTableForRender:
    def test_builds_render_rows(self):
        table = prepare_table_for_render(
            {
                "columns": ["Region", "Total"],
                "rows": [["EMEA", "100"]],
                "numeric_columns": [False, True],
            }
        )
        assert table["render_rows"] == [
            [
                {"value": "EMEA", "mono": False, "width": "fill"},
                {"value": "100", "mono": True, "width": "narrow"},
            ]
        ]
        assert "ch" in table["grid_template_columns"]
        assert "minmax(max-content, 1fr)" in table["grid_template_columns"]


class TestColumnWidths:
    def test_infers_narrow_fill_narrow_for_albums(self):
        widths = infer_column_widths(
            columns=["ID Álbum", "Título", "ID Artista"],
            rows=[
                ["1", "For Those About To Rock We Salute You", "1"],
                ["10", "Audioslave", "8"],
            ],
            numeric_columns=[True, False, True],
        )
        assert widths == ["narrow", "fill", "narrow"]

    def test_explicit_column_widths(self):
        payload = validate_table_input(
            columns=["A", "B", "C"],
            rows=[["1", "Long title here", "9"]],
            column_widths=["narrow", "fill", "narrow"],
        )
        assert payload["column_widths"] == ["narrow", "fill", "narrow"]
        grid = build_grid_template_columns(
            payload["column_widths"],
            payload["columns"],
            payload["rows"],
        )
        assert "ch" in grid
        assert "1fr" in grid

    def test_rejects_invalid_width(self):
        with pytest.raises(ValueError, match="Invalid column width"):
            validate_table_input(
                columns=["A"],
                rows=[["1"]],
                column_widths=["wide"],
            )

    def test_tool_accepts_column_widths(self):
        result = json.loads(
            invoke_show_data_table(
                columns=["ID", "Nombre"],
                rows=[["1", "Alpha"]],
                column_widths=["narrow", "fill"],
            )
        )
        assert result["displayed_to_user"] is True
        assert "column_widths" not in result


class TestShowDataTableTool:
    def test_success_response_omits_rows_from_agent_payload(self):
        result = json.loads(
            invoke_show_data_table(
                columns=["Artist", "Revenue"],
                rows=[["AC/DC", "$50.00"]],
            )
        )
        assert result["ok"] is True
        assert result["displayed_to_user"] is True
        assert result["row_count"] == 1
        assert "rows" not in result
        assert "columns" not in result
        assert "agent_instruction" in result

    def test_error_response(self):
        result = json.loads(
            invoke_show_data_table(
                columns=["A", "B"],
                rows=[["only one"]],
            )
        )
        assert result["ok"] is False
        assert "expected 2" in result["error"]

    def test_stores_payload_for_stream_resolution(self):
        invoke_show_data_table(columns=["Artist"], rows=[["AC/DC"]])
        payload = pop_table_display("call_test")
        assert payload is not None
        assert payload["rows"] == [["AC/DC"]]
        assert pop_table_display("call_test") is None
