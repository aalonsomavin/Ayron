import json

import pytest
from django.conf import settings

from apps.agent.tools.sql import (
    DEMO_TABLES,
    describe_table,
    list_tables,
    run_sql_query,
    validate_select_only,
    validate_table_name,
)


def invoke_run_sql_query(
    sql: str,
    tool_call_id: str = "call_sql_test",
    purpose: str = "Consulta de prueba para validar datos.",
):
    result = run_sql_query.invoke(
        {
            "type": "tool_call",
            "name": "run_sql_query",
            "id": tool_call_id,
            "args": {"sql": sql, "purpose": purpose},
        }
    )
    return result.content if hasattr(result, "content") else result


class TestValidateSelectOnly:
    def test_accepts_simple_select(self):
        assert validate_select_only("SELECT 1") == "SELECT 1"

    def test_rejects_empty_query(self):
        with pytest.raises(ValueError, match="empty"):
            validate_select_only("   ")

    def test_rejects_insert(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("INSERT INTO comercial_productos (sku) VALUES ('x')")

    def test_rejects_update(self):
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only(
                "SELECT * FROM comercial_productos; UPDATE comercial_productos SET sku = 'x'"
            )

    def test_rejects_delete(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("DELETE FROM comercial_productos")

    def test_rejects_drop(self):
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only(
                "SELECT * FROM comercial_productos WHERE sku = 'x'; DROP TABLE comercial_productos"
            )

    def test_rejects_forbidden_keyword_in_select(self):
        with pytest.raises(ValueError, match="forbidden keywords"):
            validate_select_only(
                "SELECT * FROM comercial_productos WHERE sku = 'x' AND 1 = 1 UNION DELETE FROM comercial_productos"
            )

    def test_rejects_select_into(self):
        with pytest.raises(ValueError, match="INTO clause"):
            validate_select_only("SELECT * INTO backup FROM comercial_productos")

    def test_rejects_multiple_statements(self):
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only("SELECT 1; SELECT 2")


class TestValidateTableName:
    def test_accepts_valid_name(self):
        assert validate_table_name("comercial_productos") == "comercial_productos"
        assert validate_table_name("competencia_precios") == "competencia_precios"

    def test_accepts_case_insensitive_match(self):
        assert validate_table_name("COMERCIAL_PRODUCTOS") == "comercial_productos"

    def test_rejects_invalid_name(self):
        with pytest.raises(ValueError, match="Invalid table name"):
            validate_table_name("comercial_productos; DROP TABLE crm_cuentas")

    def test_rejects_unknown_table(self):
        with pytest.raises(ValueError, match="not available"):
            validate_table_name("artist")


@pytest.mark.skipif(not settings.DEMO_DB_URL, reason="DEMO_DB_URL not configured")
class TestSqlToolsIntegration:
    def test_list_tables_returns_mexar_tables(self):
        tables = json.loads(list_tables.invoke({}))
        assert "comercial_productos" in tables
        assert "crm_oportunidades" in tables
        assert "competencia_precios" in tables
        assert set(tables).issubset(set(DEMO_TABLES))

    def test_describe_table_returns_columns(self):
        result = json.loads(describe_table.invoke({"table_name": "comercial_productos"}))
        assert result["table_name"] == "comercial_productos"
        column_names = {column["column_name"] for column in result["columns"]}
        assert "marca_comercial" in column_names
        assert "molecula" in column_names
        assert "primary_keys" in result

    def test_run_sql_query_returns_products(self):
        result = json.loads(
            invoke_run_sql_query(
                """
                        SELECT marca_comercial, molecula
                        FROM comercial_productos
                        WHERE sku = 'ASGEN'
                        LIMIT 1
                    """
            )
        )
        assert result["row_count"] == 1
        assert result["rows"][0]["marca_comercial"] == "Asgen"
        assert "Gemcitabina" in result["rows"][0]["molecula"]

    def test_run_sql_query_sales_by_area(self):
        result = json.loads(
            invoke_run_sql_query(
                """
                        SELECT a.nombre, SUM(pl.cantidad * pl.precio_unitario) AS ingreso
                        FROM comercial_pedido_lineas pl
                        JOIN comercial_productos p ON p.id = pl.producto_id
                        JOIN comercial_areas_terapeuticas a ON a.id = p.area_id
                        GROUP BY a.nombre
                        ORDER BY ingreso DESC
                        LIMIT 5
                    """
            )
        )
        assert result["row_count"] >= 1
        assert "nombre" in result["rows"][0]

    def test_run_sql_query_competencia_vs_lista(self):
        result = json.loads(
            invoke_run_sql_query(
                """
                        SELECT p.marca_comercial, p.precio_lista, r.precio_min, r.precio_max
                        FROM comercial_productos p
                        JOIN competencia_resumen r ON r.producto_id = p.id
                        WHERE p.sku = 'ARGLIPTIN-D'
                    """
            )
        )
        assert result["row_count"] == 1
        assert result["rows"][0]["marca_comercial"] == "Argliptin-D"
        assert result["rows"][0]["precio_lista"] is not None
        assert result["rows"][0]["precio_min"] is not None

    def test_run_sql_query_rejects_non_select(self):
        result = json.loads(invoke_run_sql_query("DELETE FROM comercial_productos"))
        assert result["ok"] is False
        assert "Only SELECT" in result["error"]
        assert "agent_instruction" in result

    def test_describe_table_not_found_returns_error_json(self):
        result = json.loads(describe_table.invoke({"table_name": "not_a_real_table"}))
        assert result["ok"] is False
        assert "not available" in result["error"].lower()
        assert "agent_instruction" in result

    def test_run_sql_query_db_error_returns_error_json(self):
        result = json.loads(
            invoke_run_sql_query("SELECT * FROM not_a_real_table LIMIT 1")
        )
        assert result["ok"] is False
        assert "agent_instruction" in result
        assert "hint" in result
