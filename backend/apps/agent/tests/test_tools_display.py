import pytest

from apps.agent.tools.display import get_done_display, get_tool_display


class TestGetToolDisplay:
    def test_list_tables(self):
        assert get_tool_display("list_tables") == {
            "tool_label": "Revisó tablas disponibles",
            "tool_subtitle": "Mexar Pharma",
            "tool_tag": "Base de datos",
            "tool_icon": "database",
        }

    def test_describe_table_with_name(self):
        assert get_tool_display("describe_table", {"table_name": "comercial_productos"}) == {
            "tool_label": "Describió la tabla comercial_productos",
            "tool_subtitle": "comercial_productos",
            "tool_tag": "Base de datos",
            "tool_icon": "database",
        }

    def test_describe_table_without_name(self):
        assert get_tool_display("describe_table", {}) == {
            "tool_label": "Describió una tabla",
            "tool_tag": "Base de datos",
            "tool_icon": "database",
        }

    def test_run_sql_query_truncates_long_sql(self):
        sql = "SELECT " + "a, " * 40 + "b FROM comercial_productos"
        display = get_tool_display("run_sql_query", {"sql": sql})
        assert display["tool_label"] == "Consultó datos de comercial_productos"
        assert display["tool_tag"] == "SQL"
        assert display["tool_icon"] == "terminal"
        assert display["tool_subtitle"].endswith("…")
        assert len(display["tool_subtitle"]) == 80

    def test_run_sql_query_short_sql(self):
        sql = "SELECT * FROM comercial_productos LIMIT 5"
        assert get_tool_display("run_sql_query", {"sql": sql}) == {
            "tool_label": "Consultó datos de comercial_productos",
            "tool_subtitle": sql,
            "tool_tag": "SQL",
            "tool_icon": "terminal",
        }

    def test_unknown_tool_humanizes_name(self):
        assert get_tool_display("propose_skill_revision") == {
            "tool_label": "Propose Skill Revision",
            "tool_tag": "Herramienta",
            "tool_icon": "file",
        }

    def test_show_data_table_with_row_count(self):
        assert get_tool_display(
            "show_data_table",
            {"rows": [["a"], ["b"], ["c"]]},
        ) == {
            "tool_label": "Mostró tabla con 3 filas",
            "tool_subtitle": "3 filas",
            "tool_tag": "Datos",
            "tool_icon": "chart",
        }

    def test_create_document_with_title(self):
        assert get_tool_display(
            "create_document",
            {"title": "Reporte de precios Mexar Pharma"},
        ) == {
            "tool_label": "Creó el reporte de precios Mexar Pharma",
            "tool_tag": "Word",
            "tool_icon": "file-doc",
        }

    def test_publish_html_artifact_dashboard_subtitle(self):
        assert get_tool_display(
            "publish_html_artifact",
            {"path": "/workspace/artifacts/_draft.html", "html_kind": "dashboard"},
        ) == {
            "tool_label": "Publicó reporte HTML",
            "tool_subtitle": "Dashboard",
            "tool_tag": "HTML",
            "tool_icon": "code",
        }

    def test_validate_html_artifact_subtitle(self):
        assert get_tool_display(
            "validate_html_artifact",
            {"path": "/workspace/artifacts/_draft.html"},
        ) == {
            "tool_label": "Validó HTML del workspace",
            "tool_subtitle": "HTML",
            "tool_tag": "HTML",
            "tool_icon": "code",
        }

    def test_write_todos_with_count(self):
        assert get_tool_display(
            "write_todos",
            {"todos": [{"content": "Paso 1"}, {"content": "Paso 2"}]},
        ) == {
            "tool_label": "Planificó 2 pasos",
            "tool_tag": "Plan",
            "tool_icon": "list-checks",
        }

    def test_get_done_display(self):
        assert get_done_display() == {
            "tool_label": "Listo",
            "tool_icon": "check-circle",
        }

    def test_read_file_with_path(self):
        assert get_tool_display(
            "read_file",
            {"file_path": "/workspace/artifacts/_draft.html"},
        ) == {
            "tool_label": "Leyó _draft.html",
            "tool_subtitle": "/workspace/artifacts/_draft.html",
            "tool_tag": "Archivo",
            "tool_icon": "file",
        }

    def test_write_file_without_path(self):
        assert get_tool_display("write_file") == {
            "tool_label": "Escribió un archivo",
            "tool_tag": "Archivo",
            "tool_icon": "file",
        }

    def test_edit_file_with_path(self):
        assert get_tool_display(
            "edit_file",
            {"path": "/workspace/artifacts/_draft.html"},
        ) == {
            "tool_label": "Editó _draft.html",
            "tool_subtitle": "/workspace/artifacts/_draft.html",
            "tool_tag": "Archivo",
            "tool_icon": "file",
        }
