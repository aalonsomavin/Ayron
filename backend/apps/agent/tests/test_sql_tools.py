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


class TestValidateSelectOnly:
    def test_accepts_simple_select(self):
        assert validate_select_only("SELECT 1") == "SELECT 1"

    def test_rejects_empty_query(self):
        with pytest.raises(ValueError, match="empty"):
            validate_select_only("   ")

    def test_rejects_insert(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("INSERT INTO agricola_lotes (codigo) VALUES ('x')")

    def test_rejects_update(self):
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only(
                "SELECT * FROM agricola_lotes; UPDATE agricola_lotes SET codigo = 'x'"
            )

    def test_rejects_delete(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("DELETE FROM agricola_lotes")

    def test_rejects_drop(self):
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only(
                "SELECT * FROM agricola_lotes WHERE codigo = 'x'; DROP TABLE agricola_lotes"
            )

    def test_rejects_forbidden_keyword_in_select(self):
        with pytest.raises(ValueError, match="forbidden keywords"):
            validate_select_only(
                "SELECT * FROM agricola_lotes WHERE codigo = 'x' AND 1 = 1 UNION DELETE FROM agricola_lotes"
            )

    def test_rejects_select_into(self):
        with pytest.raises(ValueError, match="INTO clause"):
            validate_select_only("SELECT * INTO backup FROM agricola_lotes")

    def test_rejects_multiple_statements(self):
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only("SELECT 1; SELECT 2")


class TestValidateTableName:
    def test_accepts_valid_name(self):
        assert validate_table_name("agricola_lotes") == "agricola_lotes"
        assert validate_table_name("ganaderia_animales") == "ganaderia_animales"

    def test_accepts_case_insensitive_match(self):
        assert validate_table_name("AGRICOLA_LOTES") == "agricola_lotes"

    def test_rejects_invalid_name(self):
        with pytest.raises(ValueError, match="Invalid table name"):
            validate_table_name("agricola_lotes; DROP TABLE ganaderia_corrales")

    def test_rejects_unknown_table(self):
        with pytest.raises(ValueError, match="not available"):
            validate_table_name("artist")


@pytest.mark.skipif(not settings.DEMO_DB_URL, reason="DEMO_DB_URL not configured")
class TestSqlToolsIntegration:
    def test_list_tables_returns_yivtol_tables(self):
        tables = json.loads(list_tables.invoke({}))
        assert "agricola_lotes" in tables
        assert "ganaderia_animales" in tables
        assert "yivtol_vuelos" in tables
        assert set(tables).issubset(set(DEMO_TABLES))

    def test_describe_table_returns_columns(self):
        result = json.loads(describe_table.invoke({"table_name": "agricola_lotes"}))
        assert result["table_name"] == "agricola_lotes"
        column_names = {column["column_name"] for column in result["columns"]}
        assert "codigo" in column_names
        assert "cultivo" in column_names
        assert "primary_keys" in result

    def test_run_sql_query_returns_lote_7(self):
        result = json.loads(
            run_sql_query.invoke(
                {
                    "sql": """
                        SELECT codigo, cultivo, superficie_ha
                        FROM agricola_lotes
                        WHERE codigo = 'Lote 7'
                        LIMIT 1
                    """
                }
            )
        )
        assert result["row_count"] == 1
        assert result["rows"][0]["codigo"] == "Lote 7"
        assert result["rows"][0]["cultivo"] == "Soja"

    def test_run_sql_query_lote_ranking(self):
        result = json.loads(
            run_sql_query.invoke(
                {
                    "sql": """
                        SELECT l.codigo, m.rinde_proyectado_kg_ha
                        FROM agricola_mediciones m
                        JOIN agricola_lotes l ON l.id = m.lote_id
                        JOIN yivtol_vuelos v ON v.id = m.vuelo_id
                        ORDER BY m.rinde_proyectado_kg_ha DESC
                        LIMIT 5
                    """
                }
            )
        )
        assert result["row_count"] >= 1
        assert "codigo" in result["rows"][0]

    def test_run_sql_query_corral_5_alerts(self):
        result = json.loads(
            run_sql_query.invoke(
                {
                    "sql": """
                        SELECT codigo, cabezas_actuales
                        FROM ganaderia_corrales
                        WHERE codigo = 'Corral 5'
                    """
                }
            )
        )
        assert result["row_count"] == 1
        assert result["rows"][0]["codigo"] == "Corral 5"
        assert result["rows"][0]["cabezas_actuales"] == 495

    def test_run_sql_query_rejects_non_select(self):
        result = json.loads(run_sql_query.invoke({"sql": "DELETE FROM agricola_lotes"}))
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
            run_sql_query.invoke({"sql": "SELECT * FROM not_a_real_table LIMIT 1"})
        )
        assert result["ok"] is False
        assert "agent_instruction" in result
        assert "hint" in result
