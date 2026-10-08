"""Environment / auth configuration for the TelcoABC Retention Command Center."""
import os
from functools import lru_cache

from databricks.sdk import WorkspaceClient

# Detect whether we are running inside a Databricks App (SP creds auto-injected)
IS_DATABRICKS_APP = bool(os.environ.get("DATABRICKS_APP_NAME"))

# Data location (override via env; see .env.example)
CATALOG = os.environ.get("TELCOABC_CATALOG", "main")
SCHEMA = os.environ.get("TELCOABC_SCHEMA", "telcoabc_retention")
FQ = f"{CATALOG}.{SCHEMA}"
WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")

# MAS serving endpoint (name of the deployed Multi-Agent Supervisor endpoint)
MAS_ENDPOINT = os.environ.get("SERVING_ENDPOINT", "")


@lru_cache(maxsize=1)
def get_workspace_client() -> WorkspaceClient:
    """Authenticated WorkspaceClient (service principal in-app, CLI profile locally)."""
    if IS_DATABRICKS_APP:
        return WorkspaceClient()
    profile = os.environ.get("DATABRICKS_PROFILE", "DEFAULT")
    return WorkspaceClient(profile=profile)


def get_workspace_host() -> str:
    """Workspace host URL, always with https:// scheme."""
    if IS_DATABRICKS_APP:
        host = os.environ.get("DATABRICKS_HOST", "")
        if host and not host.startswith("http"):
            host = f"https://{host}"
        return host
    return get_workspace_client().config.host


def get_sp_token() -> str:
    """Service-principal / profile OAuth token for calling serving endpoints."""
    w = get_workspace_client()
    if w.config.token:
        return w.config.token
    headers = w.config.authenticate()
    if headers and "Authorization" in headers:
        return headers["Authorization"].replace("Bearer ", "")
    raise RuntimeError("Unable to obtain workspace auth token")
