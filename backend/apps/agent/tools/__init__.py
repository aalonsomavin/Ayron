from apps.agent.tools.chart import show_chart
from apps.agent.tools.document import (
    create_document,
    get_document,
    list_conversation_files,
    update_document,
)
from apps.agent.tools.sql import describe_table, list_tables, run_sql_query
from apps.agent.tools.table import show_data_table

AGENT_TOOLS = [
    list_tables,
    describe_table,
    run_sql_query,
    show_data_table,
    show_chart,
    create_document,
    list_conversation_files,
    get_document,
    update_document,
]
SQL_TOOLS = [
    list_tables,
    describe_table,
    run_sql_query,
    show_data_table,
    show_chart,
]

__all__ = [
    "AGENT_TOOLS",
    "SQL_TOOLS",
    "create_document",
    "describe_table",
    "get_document",
    "list_conversation_files",
    "list_tables",
    "run_sql_query",
    "show_chart",
    "show_data_table",
    "update_document",
]
