from apps.agent.tools.clarification import ask_clarification
from apps.agent.tools.chart import show_chart
from apps.integrations.data_access import DATA_ACCESS_TOOL_SPECS
from apps.agent.tools.document import (
    create_document,
    get_document,
    list_conversation_files,
    update_document,
)
from apps.agent.tools.spreadsheet import (
    create_spreadsheet,
    get_spreadsheet,
    update_spreadsheet,
)
from apps.agent.tools.html_report import (
    hydrate_html_artifact,
    publish_html_artifact,
    validate_html_artifact,
)
from apps.agent.tools.sql import describe_table, list_tables, run_sql_query
from apps.agent.tools.table import show_data_table

AGENT_TOOLS = [
    list_tables,
    describe_table,
    run_sql_query,
    show_data_table,
    show_chart,
    ask_clarification,
    create_document,
    create_spreadsheet,
    hydrate_html_artifact,
    validate_html_artifact,
    publish_html_artifact,
    list_conversation_files,
    get_document,
    get_spreadsheet,
    update_document,
    update_spreadsheet,
]
SQL_TOOLS = [
    list_tables,
    describe_table,
    run_sql_query,
    show_data_table,
    show_chart,
]

DATA_ACCESS_TOOLS = DATA_ACCESS_TOOL_SPECS

__all__ = [
    "AGENT_TOOLS",
    "SQL_TOOLS",
    "DATA_ACCESS_TOOLS",
    "create_document",
    "create_spreadsheet",
    "describe_table",
    "get_document",
    "get_spreadsheet",
    "hydrate_html_artifact",
    "list_conversation_files",
    "list_tables",
    "publish_html_artifact",
    "run_sql_query",
    "show_chart",
    "ask_clarification",
    "show_data_table",
    "update_document",
    "update_spreadsheet",
    "validate_html_artifact",
]
