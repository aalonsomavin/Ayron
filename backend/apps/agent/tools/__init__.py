from apps.agent.tools.chart import show_chart
from apps.agent.tools.document import (
    create_document,
    get_document,
    list_conversation_files,
    update_document,
)
from apps.agent.tools.html_report import (
    append_html_report_block,
    create_html_report,
    get_html_report,
    publish_html_report,
    update_html_report,
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
    create_html_report,
    append_html_report_block,
    publish_html_report,
    list_conversation_files,
    get_document,
    get_html_report,
    update_document,
    update_html_report,
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
    "create_html_report",
    "append_html_report_block",
    "publish_html_report",
    "describe_table",
    "get_document",
    "get_html_report",
    "list_conversation_files",
    "list_tables",
    "run_sql_query",
    "show_chart",
    "show_data_table",
    "update_document",
    "update_html_report",
]
