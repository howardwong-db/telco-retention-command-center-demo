"""Read gold tables via the SQL warehouse using the app service principal."""
from databricks.sdk.service.sql import StatementState

from .config import get_workspace_client, WAREHOUSE_ID


def run_query(statement: str) -> list[dict]:
    """Execute SQL against the warehouse and return a list of row dicts."""
    w = get_workspace_client()
    resp = w.statement_execution.execute_statement(
        statement=statement,
        warehouse_id=WAREHOUSE_ID,
        wait_timeout="50s",
    )
    # Poll if not finished within wait_timeout
    statement_id = resp.statement_id
    while resp.status and resp.status.state in (
        StatementState.PENDING,
        StatementState.RUNNING,
    ):
        resp = w.statement_execution.get_statement(statement_id)

    if not resp.status or resp.status.state != StatementState.SUCCEEDED:
        err = resp.status.error.message if (resp.status and resp.status.error) else "unknown error"
        raise RuntimeError(f"SQL failed: {err}")

    cols = [c.name for c in resp.manifest.schema.columns] if resp.manifest and resp.manifest.schema else []
    data = resp.result.data_array if (resp.result and resp.result.data_array) else []
    return [dict(zip(cols, row)) for row in data]


def num(v, default=0.0):
    """Coerce a SQL string value to float."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default
