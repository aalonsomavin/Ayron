import json

import pytest
from django.conf import settings

from apps.agent.tools.sql import (
    describe_table,
    list_tables,
    normalize_chinook_sql,
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
            validate_select_only("INSERT INTO artist (name) VALUES ('x')")

    def test_rejects_update(self):
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only("SELECT * FROM artist; UPDATE artist SET name = 'x'")

    def test_rejects_delete(self):
        with pytest.raises(ValueError, match="Only SELECT"):
            validate_select_only("DELETE FROM artist")

    def test_rejects_drop(self):
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only("SELECT * FROM artist WHERE name = 'x'; DROP TABLE artist")

    def test_rejects_forbidden_keyword_in_select(self):
        with pytest.raises(ValueError, match="forbidden keywords"):
            validate_select_only("SELECT * FROM artist WHERE name = 'x' AND 1 = 1 UNION DELETE FROM artist")

    def test_rejects_select_into(self):
        with pytest.raises(ValueError, match="INTO clause"):
            validate_select_only("SELECT * INTO backup FROM artist")

    def test_rejects_multiple_statements(self):
        with pytest.raises(ValueError, match="Multiple SQL statements"):
            validate_select_only("SELECT 1; SELECT 2")


class TestValidateTableName:
    def test_accepts_valid_name(self):
        assert validate_table_name("album") == "Album"

    def test_rejects_invalid_name(self):
        with pytest.raises(ValueError, match="Invalid table name"):
            validate_table_name("album; DROP TABLE artist")


class TestNormalizeChinookSql:
    def test_quotes_unquoted_table(self):
        sql = normalize_chinook_sql("SELECT * FROM Album LIMIT 5")
        assert sql == 'SELECT * FROM "Album" LIMIT 5'

    def test_quotes_lowercase_table(self):
        sql = normalize_chinook_sql("SELECT * FROM album LIMIT 5")
        assert sql == 'SELECT * FROM "Album" LIMIT 5'

    def test_preserves_already_quoted_identifiers(self):
        sql = normalize_chinook_sql('SELECT "ArtistId", "Name" FROM "Artist"')
        assert sql == 'SELECT "ArtistId", "Name" FROM "Artist"'

    def test_quotes_columns_in_join(self):
        sql = normalize_chinook_sql(
            "SELECT a.Title FROM Album a JOIN Artist ar ON a.ArtistId = ar.ArtistId"
        )
        assert '"Album"' in sql
        assert '"Artist"' in sql
        assert '"Title"' in sql
        assert '"ArtistId"' in sql

    def test_preserves_string_literals(self):
        sql = normalize_chinook_sql("SELECT Name FROM Artist WHERE Name = 'AC/DC'")
        assert sql.endswith("WHERE \"Name\" = 'AC/DC'")


@pytest.mark.skipif(not settings.DEMO_DB_URL, reason="DEMO_DB_URL not configured")
class TestSqlToolsIntegration:
    def test_list_tables_returns_chinook_tables(self):
        tables = json.loads(list_tables.invoke({}))
        assert "Artist" in tables
        assert "Album" in tables

    def test_describe_table_returns_columns(self):
        result = json.loads(describe_table.invoke({"table_name": "Artist"}))
        assert result["table_name"] == "Artist"
        column_names = {column["column_name"] for column in result["columns"]}
        assert "ArtistId" in column_names
        assert "Name" in column_names
        assert "primary_keys" in result

    def test_run_sql_query_returns_rows(self):
        result = json.loads(
            run_sql_query.invoke(
                {"sql": 'SELECT "ArtistId", "Name" FROM "Artist" ORDER BY "ArtistId" LIMIT 3'}
            )
        )
        assert result["row_count"] == 3
        assert result["truncated"] is False
        assert result["rows"][0]["Name"]

    def test_run_sql_query_accepts_unquoted_table(self):
        result = json.loads(run_sql_query.invoke({"sql": "SELECT * FROM Album LIMIT 3"}))
        assert result["row_count"] == 3
        assert "Title" in result["rows"][0]

    def test_run_sql_query_rejects_non_select(self):
        result = json.loads(run_sql_query.invoke({"sql": "DELETE FROM artist"}))
        assert result["ok"] is False
        assert "Only SELECT" in result["error"]
        assert "agent_instruction" in result

    def test_describe_table_not_found_returns_error_json(self):
        result = json.loads(describe_table.invoke({"table_name": "NotARealTable"}))
        assert result["ok"] is False
        assert "not found" in result["error"].lower()
        assert "agent_instruction" in result

    def test_run_sql_query_db_error_returns_error_json(self):
        result = json.loads(
            run_sql_query.invoke({"sql": 'SELECT * FROM "NotARealTable" LIMIT 1'})
        )
        assert result["ok"] is False
        assert "agent_instruction" in result
        assert "hint" in result
