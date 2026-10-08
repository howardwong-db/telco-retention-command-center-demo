#!/usr/bin/env bash
# Lakehouse -> Lakebase forward sync, as code (not UI): sync the governed UC table
# gold_churn_risk_scores into Lakebase READ-ONLY as <schema>.synced_churn_risk_scores.
#
# Usage: PROFILE, CATALOG, SCHEMA, LAKEBASE_INSTANCE, LAKEBASE_DB from env or args.
set -euo pipefail
PROFILE="${PROFILE:-DEFAULT}"
CATALOG="${TELCOABC_CATALOG:-main}"
SCHEMA="${TELCOABC_SCHEMA:-telcoabc_retention}"
LAKEBASE_INSTANCE="${LAKEBASE_INSTANCE:-<lakebase-instance>}"
LAKEBASE_DB="${LAKEBASE_DB:-<lakebase-db>}"

databricks database create-synced-database-table --profile "$PROFILE" --json "{
  \"name\": \"${CATALOG}.${SCHEMA}.synced_churn_risk_scores\",
  \"database_instance_name\": \"${LAKEBASE_INSTANCE}\",
  \"logical_database_name\": \"${LAKEBASE_DB}\",
  \"spec\": {
    \"source_table_full_name\": \"${CATALOG}.${SCHEMA}.gold_churn_risk_scores\",
    \"primary_key_columns\": [\"customer_id\"],
    \"scheduling_policy\": \"SNAPSHOT\",
    \"new_pipeline_spec\": {\"storage_catalog\": \"${CATALOG}\", \"storage_schema\": \"${SCHEMA}\"}
  }
}"
