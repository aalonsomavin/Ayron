import pytest

from apps.agent.tools.display import get_tool_display


class TestGetToolDisplay:
    def test_list_tables(self):
        assert get_tool_display("list_tables") == {
            "tool_label": "Listar tablas",
            "tool_subtitle": "Base Chinook",
        }

    def test_describe_table_with_name(self):
        assert get_tool_display("describe_table", {"table_name": "Artist"}) == {
            "tool_label": "Describir tabla",
            "tool_subtitle": "Artist",
        }

    def test_describe_table_without_name(self):
        assert get_tool_display("describe_table", {}) == {
            "tool_label": "Describir tabla",
        }

    def test_run_sql_query_truncates_long_sql(self):
        sql = "SELECT " + "a, " * 40 + "b FROM \"Album\""
        display = get_tool_display("run_sql_query", {"sql": sql})
        assert display["tool_label"] == "Buscando datos"
        assert display["tool_subtitle"].endswith("…")
        assert len(display["tool_subtitle"]) == 80

    def test_run_sql_query_short_sql(self):
        sql = 'SELECT * FROM "Artist" LIMIT 5'
        assert get_tool_display("run_sql_query", {"sql": sql}) == {
            "tool_label": "Buscando datos",
            "tool_subtitle": sql,
        }

    def test_unknown_tool_humanizes_name(self):
        assert get_tool_display("propose_skill_revision") == {
            "tool_label": "Propose Skill Revision",
        }
