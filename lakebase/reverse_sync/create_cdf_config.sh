#!/usr/bin/env bash
# Reverse Lakehouse Sync as code (NOT UI): Lakebase Change Data Feed streams the
# writable Postgres `ops` schema into open-format Delta tables in Unity Catalog with
# SCD Type-2-style change history (_pg_change_type, _pg_lsn, _timestamp, ...).
#
# Set your Lakebase instance/db and target catalog via env or edit the defaults.
set -euo pipefail
PROFILE="${PROFILE:-DEFAULT}"
CATALOG="${TELCOABC_CATALOG:-main}"
LAKEBASE_INSTANCE="${LAKEBASE_INSTANCE:-<lakebase-instance>}"
LAKEBASE_DB="${LAKEBASE_DB:-<lakebase-db>}"

databricks postgres create-cdf-config \
  "projects/${LAKEBASE_INSTANCE}/branches/production/databases/${LAKEBASE_DB}" \
  "${CATALOG}" lakebase_cdf ops \
  --cdf-config-id ops_reverse_sync \
  --profile "$PROFILE"
