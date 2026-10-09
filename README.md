# TelcoABC Retention Command Center

A complete, reproducible Databricks demo for a telecom/cable **churn & retention prevention command center**: it equips call-center retention agents with real-time churn risk scores, competitor talk tracks, and AI-recommended save offers, all on one Databricks platform. The whole thing is synthetic and self-contained, so you can deploy it to your own workspace and present it end-to-end.

> New here? Read **[docs/TALK_TRACK.md](docs/TALK_TRACK.md)** for the demo narrative and **[docs/PROMPTS.md](docs/PROMPTS.md)** for the AI prompts and the one-shot build prompt.

## Disclaimer

> **Disclaimer — demonstration asset.** All data in this project is synthetic and generated for illustration only. "TelcoABC" is a fictional company. Competitor names (e.g., T-Mobile, AT&T, Verizon, Frontier, Google Fiber) and the associated "playbooks" appear **solely for illustrative purposes** and do **not** represent, and are **not affiliated with or endorsed by**, those companies. Any stated "weaknesses," pricing, offers, or save-rate figures are **fabricated sample data**, not factual claims about any real company. This project is a demo and is **not intended for production use**.

## Architecture (7 layers)

See `dashboard/architecture_diagram.png`.

1. **Ingestion** — a Python + Faker generator lands 6 raw JSON sources into a Unity Catalog Volume.
2. **Spark Declarative Pipeline** — Auto Loader ingests the Volume into **Bronze** streaming tables; materialized views transform Bronze → **Gold** (6 gold tables).
3. **ML churn scoring** — an MLflow-tracked Gradient Boosted Trees model (test AUC ~0.89) writes per-customer `gold_churn_risk_scores`.
4. **Genie space** — natural-language analytics over the gold tables.
5. **Knowledge Assistant (RAG)** — competitor playbooks, talk tracks, coaching guide, offer catalog.
6. **Multi-Agent Supervisor (MAS)** — routes across Genie + Knowledge Assistant and synthesizes one answer.
7. **Serving** — an **AI/BI dashboard** and a **Databricks App** (4 tabs) read the gold tables and call the MAS; **Lakebase** persists app chat.

## Repository layout

| Path | What it is |
|---|---|
| `data_generation/` | `generate_bronze.py` (lands 6 JSON sources, deterministic seed 42) and `train_churn_model.py` (MLflow GBT → churn scores) |
| `pipeline/transformations/` | `01_bronze.sql` (Auto Loader `read_files`) + `02_gold.sql` (gold medallion) |
| `notebooks/` | `01_data_ingestion_showcase.py` — incremental drop + `ai_classify` topic labeling |
| `agent_bricks/` | `genie_agent.json` (Genie config) + `playbooks/*.md` (Knowledge Assistant RAG docs) |
| `dashboard/` | `telcoabc_retention_dashboard_native.lvdash.json` + architecture diagram |
| `app/` | Databricks App — FastAPI backend (`app.py`, `server/`) + React frontend (`frontend/`, built `frontend/dist/`) |
| `lakebase/` | Postgres schema, seed, sync, and reverse-sync (CDF) scripts for chat persistence |
| `databricks.yml` | Asset Bundle: pipeline + refresh job + app |
| `docs/` | `PROMPTS.md`, `TALK_TRACK.md` |

## Prerequisites

- A Databricks workspace with **serverless compute** and **Unity Catalog** enabled.
- A **SQL warehouse** (used by the Genie space, dashboard, and app).
- **Databricks CLI v1.x** with bundles (`databricks bundle --help` works) and a configured profile.
- **Agent Bricks** access (to create the Genie space, Knowledge Assistant, and MAS).
- Python 3.12 + `databricks-connect`, `faker`, `numpy`, `pandas`, `scikit-learn`, `mlflow` for the generators.
- Node 18+ only if you want to rebuild the frontend (a built `frontend/dist/` is already included).

## Configure

```bash
cp .env.example .env
# then edit .env: DATABRICKS_PROFILE, TELCOABC_CATALOG, TELCOABC_SCHEMA,
# DATABRICKS_WAREHOUSE_ID, SERVING_ENDPOINT, Lakebase + MLflow values
```

Also set your workspace host in `databricks.yml` (or just select it via your CLI profile with `-p <profile>`), and set `catalog` / `warehouse_id` / `mas_endpoint_name` there (or pass `--var`).

A few artifacts carry `<CATALOG>` / `<SCHEMA>` placeholders that must be substituted before use (they can't read env vars): `pipeline/transformations/01_bronze.sql` (Volume paths), `agent_bricks/genie_agent.json` (table identifiers), and `dashboard/telcoabc_retention_dashboard_native.lvdash.json` (dataset references). Substitute with your values, e.g.:

```bash
sed -i '' "s/<CATALOG>/$TELCOABC_CATALOG/g" \
  pipeline/transformations/01_bronze.sql \
  agent_bricks/genie_agent.json \
  dashboard/telcoabc_retention_dashboard_native.lvdash.json
```

## Deploy (in order)

1. **Bundle deploy** the pipeline, refresh job, and app:
   ```bash
   databricks bundle deploy -p <profile>
   ```
2. **Generate + land the data** (creates the catalog/schema/Volume as needed, then lands 6 JSON sources):
   ```bash
   python data_generation/generate_bronze.py
   ```
3. **Run the pipeline** (Bronze → Gold). Use the Pipelines UI, or the CLI. First run or a reset uses the full-refresh flag (note: it is `--full-refresh`, **not** `--full-refresh-all`):
   ```bash
   databricks pipelines start-update <pipeline_id> --full-refresh -p <profile>
   ```
4. **Score churn** (writes `gold_churn_risk_scores`):
   ```bash
   python data_generation/train_churn_model.py
   ```
   (This also runs as the `score_churn` job task after the pipeline.)
5. **Create the Agent Bricks:**
   - Genie space from `agent_bricks/genie_agent.json` (over the 6 gold tables).
   - Knowledge Assistant over `agent_bricks/playbooks/*.md`.
   - A **Multi-Agent Supervisor** with two tools: the Genie space (analytics) and the Knowledge Assistant (playbooks). Note its endpoint name and set `SERVING_ENDPOINT` / `mas_endpoint_name`.
6. **Import the dashboard:**
   ```bash
   databricks lakeview create --serialized-dashboard "$(cat dashboard/telcoabc_retention_dashboard_native.lvdash.json)" -p <profile>
   # then publish it to the SQL warehouse
   ```
7. **Grant the app's service principal** (the one Databricks creates for the app) access to **every** resource it needs:
   - `USE CATALOG` + `USE SCHEMA` + `SELECT` on the schema
   - `CAN_RUN` on the **Genie space**
   - `CAN_QUERY` on the **Knowledge Assistant** serving endpoint
   - `CAN_QUERY` on the **MAS** serving endpoint

   > ⚠️ **Key gotcha — MAS runs downstream tools AS THE CALLER (the app's service principal).** So the SP needs **direct** access to the Genie space AND the Knowledge Assistant endpoint, not just the MAS endpoint. Miss one and that routing path silently falls back or errors (e.g. "I don't have access to the playbooks"). Attaching the serving-endpoint + sql-warehouse resources in `databricks.yml`/`app.yaml` only auto-grants the MAS endpoint and warehouse; the Genie and KA grants are manual.

## Verify

- All 4 app tabs load real gold data (Executive Dashboard, AI Assistant, Competitor Intelligence, Agent Coaching).
- `GET /api/me` returns your email.
- MAS chat round-trips on **both** paths:
  - analytics (Genie): *"What's our current churn rate vs baseline?"*
  - playbook (KA): *"What's the best retention offer against T-Mobile Home Internet, and why?"*
  The MAS should synthesize numbers + talk track into one answer (~15–33s).

## Documentation

- **[docs/TALK_TRACK.md](docs/TALK_TRACK.md)** — presenter guide: the hook, the 4-act demo flow, and live MAS questions.
- **[docs/PROMPTS.md](docs/PROMPTS.md)** — the demo's AI prompts (Genie / KA / MAS / `ai_classify`) and the one-shot build prompt to regenerate or adapt the whole demo.

## License

Licensed under the Apache License 2.0 — see [LICENSE](LICENSE). Copyright 2026 Databricks, Inc.
