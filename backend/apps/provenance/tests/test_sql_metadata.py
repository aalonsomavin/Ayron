from apps.provenance.sql_metadata import columns_from_rows, extract_sql_tables


class TestExtractSqlTables:
    def test_single_from(self):
        sql = "SELECT * FROM comercial_productos LIMIT 5"
        assert extract_sql_tables(sql) == ["comercial_productos"]

    def test_join_deduplicates(self):
        sql = """
            SELECT p.marca_comercial
            FROM comercial_productos p
            JOIN comercial_areas_terapeuticas a ON a.id = p.area_id
        """
        assert extract_sql_tables(sql) == [
            "comercial_productos",
            "comercial_areas_terapeuticas",
        ]


class TestColumnsFromRows:
    def test_empty_rows(self):
        assert columns_from_rows([]) == []

    def test_uses_first_row_keys(self):
        rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        assert columns_from_rows(rows) == ["a", "b"]
