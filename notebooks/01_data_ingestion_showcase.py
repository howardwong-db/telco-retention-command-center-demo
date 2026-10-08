# Databricks notebook source
# MAGIC %md
# MAGIC # TelcoABC Retention — Data Ingestion Showcase
# MAGIC
# MAGIC This notebook demonstrates the ingestion story for the Retention Command Center:
# MAGIC
# MAGIC 1. **Generate** a fresh batch of raw retention-call records and **land** them as JSON
# MAGIC    into a Unity Catalog **Volume** (simulating a new drop from the contact-center system).
# MAGIC 2. **Ingest** that landing zone into **Bronze** with the Spark Declarative Pipeline
# MAGIC    (Auto Loader picks up only the new files), then run the **Bronze → Gold** transforms
# MAGIC    in the same pipeline.
# MAGIC 3. **Showcase `ai_classify`** — auto-label the free-text customer mention into a call
# MAGIC    topic, so topic analytics can run even on un-labeled raw calls.

# COMMAND ----------

import os
CATALOG = os.environ.get("TELCOABC_CATALOG", "main")   # set to your catalog
SCHEMA = os.environ.get("TELCOABC_SCHEMA", "telcoabc_retention")
LANDING = f"/Volumes/{CATALOG}/{SCHEMA}/landing"
spark.sql(f"USE {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Generate & land a new batch of raw call records
# MAGIC A small incremental drop (500 new calls) written as JSON into the same landing folder
# MAGIC the pipeline watches. In a real deployment this file arrives from the telephony/CRM export.

# COMMAND ----------

from pyspark.sql import functions as F
from datetime import datetime

topics_seed = [
    ("T-Mobile is offering me $50/mo flat, why am I paying so much", "COMP-01"),
    ("my bill went up again after the promo ended", None),
    ("internet is unusable in the evenings, so slow", None),
    ("AT&T offered free install and cheaper fiber", "COMP-02"),
    ("I've been loyal 10 years and get nothing", None),
    ("thinking of dropping cable TV, I only stream now", None),
    ("interested in adding a mobile line to my plan", None),
    ("third outage this month, this is ridiculous", None),
]

base = spark.range(0, 500).withColumn("seed_idx", (F.col("id") % len(topics_seed)).cast("int"))
seed_df = spark.createDataFrame(
    [(i, t, c) for i, (t, c) in enumerate(topics_seed)],
    ["seed_idx", "mention_text", "competitor_id"])

new_calls = (base.join(seed_df, "seed_idx")
    .withColumn("call_id", F.concat(F.lit("CALL-NEW-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("customer_id", F.concat(F.lit("CUST-"), F.lpad((F.col("id") * 7 % 50000).cast("string"), 6, "0")))
    .withColumn("agent_id", F.concat(F.lit("AGT-"), F.lpad((F.col("id") % 250 + 1).cast("string"), 4, "0")))
    .withColumn("call_date", F.date_format(F.current_date(), "yyyy-MM-dd"))
    .withColumn("handle_time_min", F.round(F.rand() * 15 + 6, 1))
    .withColumn("competitor_mentioned", F.col("competitor_id").isNotNull())
    .withColumn("offer_accepted", F.rand() < 0.5)
    .withColumn("outcome", F.when(F.rand() < 0.5, "Saved").otherwise("Pending"))
    .select("call_id", "customer_id", "agent_id", "call_date", "handle_time_min",
            "competitor_mentioned", "competitor_id", "mention_text", "offer_accepted", "outcome"))

target = f"{LANDING}/call_interactions/new_batch_{datetime.now():%Y%m%d_%H%M%S}.json"
new_calls.coalesce(1).write.mode("append").json(f"{LANDING}/call_interactions")
print(f"Landed {new_calls.count()} new raw call records into {LANDING}/call_interactions")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Run the Spark Declarative Pipeline
# MAGIC Trigger the pipeline so Auto Loader ingests the new files into `bronze_call_interactions`
# MAGIC and the Bronze → Gold materialized views refresh. Run from the CLI or the Pipelines UI:
# MAGIC
# MAGIC ```bash
# MAGIC databricks pipelines start-update <pipeline_id> --profile <your-profile>
# MAGIC ```
# MAGIC
# MAGIC Auto Loader tracks which files it has already seen, so only the new batch is processed.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. `ai_classify` — auto-label the free-text mention into a call topic
# MAGIC The deterministic pipeline already carries `call_topic`, but raw drops may arrive
# MAGIC unlabeled. `ai_classify` reads the customer's own words and assigns one of the
# MAGIC enumerated retention topics — powering topic analytics with zero manual tagging.

# COMMAND ----------

labeled = spark.sql(f"""
  SELECT
    call_id,
    mention_text,
    ai_classify(
      mention_text,
      ARRAY(
        'Competitor Price Offer', 'Rate Increase Concern', 'Billing Dispute',
        'Slow Speed / Performance', 'Outage / Reliability', 'Promo / Contract Expiration',
        'Moving / Relocation', 'TV Value / Cord-Cutting', 'Mobile / Bundle Interest',
        'Loyalty / Feels Undervalued'
      )
    ) AS ai_call_topic
  FROM {CATALOG}.{SCHEMA}.bronze_call_interactions
  WHERE call_id LIKE 'CALL-NEW-%'
  LIMIT 20
""")
display(labeled)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Takeaway
# MAGIC The same declarative pipeline that ingested the historical data ingests each new drop,
# MAGIC and `ai_classify` turns raw customer language into governed topic labels for analysis —
# MAGIC the foundation the Genie space, dashboard, and Retention Command Center app all build on.
