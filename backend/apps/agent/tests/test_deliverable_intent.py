import pytest

from apps.agent.deliverable_intent import (
    DeliverableIntent,
    detect_deliverable_intent,
    format_deliverable_prompt_block,
    required_tools_for_intent,
)


class TestDetectDeliverableIntent:
    @pytest.mark.parametrize(
        ("message", "expected"),
        [
            ("Preparame un informe de ventas de mayo", DeliverableIntent.CREATE_HTML),
            ("Hazme un dashboard de KPIs de facturación", DeliverableIntent.CREATE_HTML),
            ("Genera un reporte exportable en PDF", DeliverableIntent.CREATE_HTML),
            ("Genera un memo en Word sobre ventas", DeliverableIntent.CREATE_DOCX),
            ("Genera una hoja Excel con ventas por región", DeliverableIntent.CREATE_XLSX),
            ("Exporta los datos en xlsx", DeliverableIntent.CREATE_XLSX),
            ("Necesito un spreadsheet con los números", DeliverableIntent.CREATE_XLSX),
            ("Necesito una carta formal para el cliente", DeliverableIntent.CREATE_DOCX),
            ("Actualiza el dashboard con los datos de junio", DeliverableIntent.UPDATE_FILE),
            ("Modifica el informe anterior", DeliverableIntent.UPDATE_FILE),
            ("Transformalo en un dashboard interactivo", DeliverableIntent.UPDATE_FILE),
            ("Conviértelo en dashboard con tabs", DeliverableIntent.UPDATE_FILE),
            ("¿Cuáles son los 5 artistas top?", DeliverableIntent.NONE),
            ("¿Cuánto vendimos en mayo?", DeliverableIntent.NONE),
            ("Muéstrame el top 10 de álbumes", DeliverableIntent.NONE),
            ("", DeliverableIntent.NONE),
        ],
    )
    def test_detect_deliverable_intent(self, message, expected):
        assert detect_deliverable_intent(message) == expected


class TestDeliverableHelpers:
    def test_required_tools_for_create_html(self):
        assert required_tools_for_intent(DeliverableIntent.CREATE_HTML) == frozenset(
            {"publish_html_artifact"}
        )

    def test_required_tools_for_update_file(self):
        assert required_tools_for_intent(DeliverableIntent.UPDATE_FILE) == frozenset(
            {"publish_html_artifact", "update_document", "update_spreadsheet"}
        )

    def test_required_tools_for_create_xlsx(self):
        assert required_tools_for_intent(DeliverableIntent.CREATE_XLSX) == frozenset(
            {"create_spreadsheet"}
        )

    def test_format_prompt_block_for_html(self):
        block = format_deliverable_prompt_block(DeliverableIntent.CREATE_HTML)
        assert "publish_html_artifact" in block
        assert "validate_html_artifact" in block
        assert "write_todos" in block

    def test_format_prompt_block_for_xlsx(self):
        block = format_deliverable_prompt_block(DeliverableIntent.CREATE_XLSX)
        assert "create_spreadsheet" in block
        assert "xlsx-spreadsheets" in block

    def test_format_prompt_block_none_is_empty(self):
        assert format_deliverable_prompt_block(DeliverableIntent.NONE) == ""
