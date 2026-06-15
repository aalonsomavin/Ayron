from apps.agent.tools.chart import show_chart
from apps.agent.tools.sql import describe_table, list_tables, run_sql_query
from apps.agent.tools.table import show_data_table

AGENT_TOOLS = [list_tables, describe_table, run_sql_query, show_data_table, show_chart]
SQL_TOOLS = AGENT_TOOLS

__all__ = [
    "AGENT_TOOLS",
    "SQL_TOOLS",
    "describe_table",
    "list_tables",
    "run_sql_query",
    "show_data_table",
    "show_chart",
]
