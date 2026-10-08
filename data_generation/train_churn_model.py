"""
ML churn scoring — trains a real MLflow-tracked model on customer + behavioral
features, then writes calibrated per-customer scores to gold_churn_risk_scores.

Calibration targets (so the story lands):
  - Critical tier (score >= 0.55): ~6,375 customers
  - Critical-tier average score: ~0.665
Runs on serverless via Databricks Connect.
"""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import mlflow

PROFILE = os.environ.get("DATABRICKS_PROFILE", "DEFAULT")
CATALOG = os.environ.get("TELCOABC_CATALOG", "main")
SCHEMA = os.environ.get("TELCOABC_SCHEMA", "telcoabc_retention")
np.random.seed(42)


def _get_spark():
    """Ambient Spark when running inside Databricks (serverless job/notebook);
    Databricks Connect to serverless when running locally."""
    if os.environ.get("DATABRICKS_RUNTIME_VERSION"):
        from pyspark.sql import SparkSession
        return SparkSession.builder.getOrCreate()
    from databricks.connect import DatabricksSession
    return DatabricksSession.builder.profile(PROFILE).serverless(True).getOrCreate()


spark = _get_spark()
spark.sql(f"USE {CATALOG}.{SCHEMA}")

# ---- Build feature table: customer profile + call behavior + service events ----
feat = spark.sql("""
WITH call_agg AS (
  SELECT customer_id,
         COUNT(*)                                        AS n_calls,
         SUM(CASE WHEN competitor_mentioned THEN 1 ELSE 0 END) AS n_competitor_calls,
         SUM(CASE WHEN outcome='Churned' THEN 1 ELSE 0 END)    AS n_churn_calls,
         MAX(CASE WHEN competitor_mentioned THEN 1 ELSE 0 END) AS ever_competitor
  FROM bronze_call_interactions GROUP BY customer_id
),
svc_agg AS (
  SELECT customer_id, COUNT(*) AS n_events,
         SUM(CASE WHEN event_type IN ('Outage','Slow Speed') THEN 1 ELSE 0 END) AS n_quality_events
  FROM bronze_service_events GROUP BY customer_id
)
SELECT c.customer_id, c.plan_type, c.has_mobile, c.tenure_months, c.monthly_spend,
       c.contract_type, c.autopay_enrolled, c.internet_speed, c.market,
       COALESCE(ca.n_calls,0) n_calls, COALESCE(ca.n_competitor_calls,0) n_competitor_calls,
       COALESCE(ca.ever_competitor,0) ever_competitor,
       COALESCE(sa.n_events,0) n_events, COALESCE(sa.n_quality_events,0) n_quality_events,
       CASE WHEN c.status='Churned' THEN 1 ELSE 0 END AS label
FROM bronze_customer_profiles c
LEFT JOIN call_agg ca USING (customer_id)
LEFT JOIN svc_agg sa USING (customer_id)
""").toPandas()

# ---- Feature engineering ----
df = feat.copy()
df["is_month_to_month"] = (df.contract_type == "Month-to-Month").astype(int)
df["is_internet_only"] = (df.plan_type == "Internet Only").astype(int)
df["no_mobile"] = (~df.has_mobile.astype(bool)).astype(int)
df["low_tenure"] = (df.tenure_months < 12).astype(int)
df["no_autopay"] = (~df.autopay_enrolled.astype(bool)).astype(int)
FEATURES = ["tenure_months", "monthly_spend", "n_calls", "n_competitor_calls",
            "ever_competitor", "n_events", "n_quality_events", "is_month_to_month",
            "is_internet_only", "no_mobile", "low_tenure", "no_autopay"]
X, y = df[FEATURES], df["label"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

# ---- Train + track with MLflow ----
mlflow.set_registry_uri("databricks-uc")
# Set MLFLOW_EXPERIMENT to a path under your own user, e.g. /Users/<you>/telcoabc_churn
mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT", "/Shared/telcoabc_churn"))
with mlflow.start_run(run_name="gbt_churn_v1") as run:
    model = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.08,
                                       subsample=0.8, random_state=42)
    model.fit(Xtr, ytr)
    auc = roc_auc_score(yte, model.predict_proba(Xte)[:, 1])
    mlflow.log_params({"n_estimators": 200, "max_depth": 4, "learning_rate": 0.08})
    mlflow.log_metric("test_auc", float(auc))
    mlflow.sklearn.log_model(model, "model")
    print(f"  trained GBT churn model — test AUC = {auc:.3f}, run_id = {run.info.run_id}")

# ---- Score all customers ----
df["raw_score"] = model.predict_proba(X)[:, 1]

# ---- Calibrate: Critical (>=0.55) ~= 6,375 customers, avg critical score ~0.665 ----
CRIT_CUTOFF = 0.55
target_critical = 6375
# rank-based rescale so the top `target_critical` land above the cutoff, mapped to a
# realistic score distribution with the desired critical-tier average.
ranks = df["raw_score"].rank(pct=True)  # 0..1
# piecewise: top slice -> [0.55, 0.95], remainder -> [0.02, 0.55]
crit_frac = target_critical / len(df)
thr = 1 - crit_frac
# critical band skewed toward the cutoff (square the position) so the tier average
# lands ~0.665 with a realistic shape: many near 0.55, few near the 0.85 max.
crit_pos = ((ranks - thr) / (1 - thr)).clip(0, 1)
score = np.where(
    ranks >= thr,
    0.55 + (crit_pos ** 2) * 0.30,                      # critical band 0.55–0.85, mean ~0.65
    0.02 + (ranks / thr) * 0.53                         # non-critical 0.02–0.55
)
df["churn_score"] = np.round(np.clip(score, 0.01, 0.99), 4)
df["risk_tier"] = np.where(df.churn_score >= 0.55, "Critical",
                    np.where(df.churn_score >= 0.40, "High",
                    np.where(df.churn_score >= 0.25, "Medium", "Low")))

crit = df[df.risk_tier == "Critical"]
print(f"  Critical tier: {len(crit):,} customers, avg score {crit.churn_score.mean():.3f}")
print(df.risk_tier.value_counts().to_string())

# ---- Recommended offer per customer (competitor-aware, else profile-based) ----
# join each critical/high customer's dominant competitor from calls
dom_comp = spark.sql("""
  SELECT customer_id, competitor_id,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY COUNT(*) DESC) rn
  FROM bronze_call_interactions WHERE competitor_mentioned=true
  GROUP BY customer_id, competitor_id
""").filter("rn=1").select("customer_id", "competitor_id").toPandas()
comp_counter = {"COMP-01":"OFF-01","COMP-02":"OFF-03","COMP-03":"OFF-01",
                "COMP-04":"OFF-04","COMP-05":"OFF-01","COMP-06":"OFF-01"}
df = df.merge(dom_comp, on="customer_id", how="left")
def rec_offer(r):
    if pd.notna(r.competitor_id) and r.competitor_id in comp_counter:
        return comp_counter[r.competitor_id]
    if r.is_internet_only: return "OFF-01"
    if r.no_mobile: return "OFF-02"
    if r.is_month_to_month: return "OFF-03"
    return "OFF-05"
df["recommended_offer_id"] = df.apply(rec_offer, axis=1)

# ---- Write gold_churn_risk_scores ----
out = df[["customer_id", "churn_score", "risk_tier", "recommended_offer_id",
          "competitor_id", "n_competitor_calls", "monthly_spend", "tenure_months",
          "plan_type", "market"]].copy()
out_sdf = spark.createDataFrame(out)
out_sdf.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.gold_churn_risk_scores")
print(f"  wrote gold_churn_risk_scores: {len(out):,} rows")
