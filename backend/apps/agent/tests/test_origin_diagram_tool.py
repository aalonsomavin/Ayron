import json

import pytest

from apps.agent.tools.origin_diagram import (
    MAX_SOURCES,
    pop_origin_diagram_display,
    prepare_origin_diagram_for_render,
    show_origin_diagram,
    validate_origin_diagram_input,
)


def invoke_show_origin_diagram(**kwargs):
    result = show_origin_diagram.invoke(
        {
            "type": "tool_call",
            "name": "show_origin_diagram",
            "id": "call_test",
            "args": kwargs,
        }
    )
    return result.content if hasattr(result, "content") else result


CONVERGE_ARGS = {
    "pattern": "converge",
    "sources": [
        {"label": "Cuentas CRM", "subtitle": "Asignación por ejecutivo"},
        {"label": "Ventas", "subtitle": "Facturación por institución"},
    ],
    "merge": {"label": "Cruce por cuenta", "detail": "JOIN por institución"},
    "result": {"label": "Ranking de ejecutivos", "subtitle": "6 filas · SUM(ventas)"},
    "caption": "dos fuentes → cruce → resultado",
    "hint": "Cuando hay un JOIN entre dos tablas.",
}


class TestValidateOriginDiagramInput:
    def test_valid_converge(self):
        payload = validate_origin_diagram_input(**CONVERGE_ARGS)
        assert payload["ok"] is True
        assert payload["pattern"] == "converge"
        assert len(payload["sources"]) == 2

    def test_valid_chain(self):
        payload = validate_origin_diagram_input(
            pattern="chain",
            sources=[{"label": "Facturas", "subtitle": "PostgreSQL · 12.4k filas"}],
            transforms=[
                {"label": "WHERE año = 2026", "detail": "filtro de fecha"},
                {"label": "SUM por mes", "detail": "GROUP BY mes"},
            ],
            result={"label": "Ingresos mensuales", "subtitle": "12 meses"},
            caption="fuente → filtros → agregación → resultado",
            hint="Cuando los datos pasan por transformaciones en cadena.",
        )
        assert payload["pattern"] == "chain"
        assert len(payload["transforms"]) == 2

    def test_valid_multi_source(self):
        payload = validate_origin_diagram_input(
            pattern="multi_source",
            sources=[
                {"label": "Ventas", "subtitle": "PostgreSQL", "icon": "database"},
                {"label": "Metas", "subtitle": "Hoja de cálculo", "icon": "sheet"},
                {"label": "Catálogo", "subtitle": "Archivo CSV", "icon": "file"},
            ],
            merge={"label": "Consolidado trimestral"},
            result={"label": "Avance vs meta"},
            caption="tres fuentes → consolidado → resultado",
            hint="Cuando combinas orígenes distintos.",
        )
        assert payload["pattern"] == "multi_source"

    def test_rejects_pattern_mismatch(self):
        with pytest.raises(ValueError, match="pattern must be chain"):
            validate_origin_diagram_input(
                pattern="converge",
                sources=[{"label": "Solo una"}],
                result={"label": "Resultado"},
                caption="cadena",
                hint="hint",
            )

    def test_merge_required_for_converge(self):
        with pytest.raises(ValueError, match="merge must be an object"):
            validate_origin_diagram_input(
                pattern="converge",
                sources=[
                    {"label": "A", "subtitle": "uno"},
                    {"label": "B", "subtitle": "dos"},
                ],
                result={"label": "Resultado"},
                caption="dos fuentes → resultado",
                hint="hint",
            )

    def test_rejects_too_many_sources(self):
        sources = [{"label": f"S{i}", "subtitle": "x"} for i in range(MAX_SOURCES + 1)]
        with pytest.raises(ValueError, match=f"Maximum {MAX_SOURCES} sources"):
            validate_origin_diagram_input(
                pattern="multi_source",
                sources=sources,
                merge={"label": "Cruce"},
                result={"label": "Resultado"},
                caption="caption",
                hint="hint",
            )

    def test_rejects_invalid_icon(self):
        with pytest.raises(ValueError, match="icon must be database"):
            validate_origin_diagram_input(
                pattern="chain",
                sources=[{"label": "Fuente", "icon": "cloud"}],
                result={"label": "Resultado"},
                caption="caption",
                hint="hint",
            )


class TestOriginDiagramRegistry:
    def test_registry_and_pop(self):
        show_origin_diagram.invoke(
            {
                "type": "tool_call",
                "name": "show_origin_diagram",
                "id": "call_reg",
                "args": CONVERGE_ARGS,
            }
        )
        stored = pop_origin_diagram_display("call_reg")
        assert stored["pattern"] == "converge"
        assert pop_origin_diagram_display("call_reg") is None

    def test_tool_returns_agent_instruction(self):
        raw = invoke_show_origin_diagram(**CONVERGE_ARGS)
        parsed = json.loads(raw)
        assert parsed["ok"] is True
        assert parsed["displayed_to_user"] is True
        assert "agent_instruction" in parsed


class TestPrepareOriginDiagramForRender:
    def test_prepare_includes_tool_call_id(self):
        payload = validate_origin_diagram_input(**CONVERGE_ARGS)
        payload["tool_call_id"] = "call_render"
        render = prepare_origin_diagram_for_render(payload)
        assert render["tool_call_id"] == "call_render"
        assert render["pattern"] == "converge"
