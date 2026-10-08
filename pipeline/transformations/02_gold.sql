-- ============================================================================
-- GOLD — curated, serving-ready marts derived from bronze.
-- (gold_churn_risk_scores is produced by the ML scoring job, not this pipeline.)
-- ============================================================================

-- Enriched call fact: calls + customer + agent + competitor + offer, with flags
CREATE OR REFRESH MATERIALIZED VIEW gold_call_interactions AS
SELECT
  c.call_id,
  c.customer_id,
  cust.market,
  cust.plan_type,
  cust.tenure_months,
  cust.monthly_spend,
  c.agent_id,
  a.agent_name,
  a.team,
  a.tier              AS agent_tier,
  CAST(c.call_date AS DATE)          AS call_date,
  date_trunc('month', c.call_date)   AS call_month,
  c.handle_time_min,
  c.competitor_mentioned,
  c.competitor_id,
  comp.competitor_name,
  c.call_topic,
  c.mention_text,
  c.offer_presented_id,
  o.offer_name        AS offer_presented,
  c.offer_accepted,
  c.outcome,
  CASE WHEN c.outcome = 'Saved'   THEN 1 ELSE 0 END AS is_saved,
  CASE WHEN c.outcome = 'Churned' THEN 1 ELSE 0 END AS is_churned
FROM bronze_call_interactions c
LEFT JOIN bronze_customer_profiles cust USING (customer_id)
LEFT JOIN bronze_agents a           USING (agent_id)
LEFT JOIN bronze_competitor_intel comp ON c.competitor_id = comp.competitor_id
LEFT JOIN bronze_retention_offers o    ON c.offer_presented_id = o.offer_id;

-- Agent performance + coaching metrics + peer ranking
CREATE OR REFRESH MATERIALIZED VIEW gold_agent_performance AS
WITH perf AS (
  SELECT
    agent_id,
    COUNT(*)                                              AS total_calls,
    SUM(is_saved)                                         AS saves,
    ROUND(AVG(is_saved), 4)                               AS save_rate,
    ROUND(AVG(handle_time_min), 1)                        AS avg_handle_time_min,
    ROUND(AVG(CASE WHEN competitor_mentioned THEN 1 ELSE 0 END), 4) AS competitor_call_rate,
    ROUND(AVG(CASE WHEN offer_accepted THEN 1 ELSE 0 END), 4)       AS offer_conversion_rate
  FROM gold_call_interactions
  GROUP BY agent_id
)
SELECT
  a.agent_id, a.agent_name, a.team, a.tier, a.nps, a.hire_date,
  p.total_calls, p.saves, p.save_rate, p.avg_handle_time_min,
  p.competitor_call_rate, p.offer_conversion_rate,
  RANK() OVER (ORDER BY p.save_rate DESC)                 AS save_rate_rank,
  ROUND(AVG(p.save_rate) OVER (), 4)                      AS team_avg_save_rate,
  ROUND(p.save_rate - AVG(p.save_rate) OVER (), 4)        AS save_rate_vs_avg
FROM bronze_agents a
JOIN perf p USING (agent_id);

-- Retention offer effectiveness, by competitor
CREATE OR REFRESH MATERIALIZED VIEW gold_retention_offers AS
WITH by_offer_comp AS (
  SELECT
    offer_presented_id AS offer_id,
    offer_presented    AS offer_name,
    competitor_id,
    competitor_name,
    COUNT(*)                       AS times_presented,
    SUM(CASE WHEN offer_accepted THEN 1 ELSE 0 END) AS times_accepted,
    ROUND(AVG(is_saved), 4)        AS save_rate
  FROM gold_call_interactions
  WHERE offer_presented_id IS NOT NULL
  GROUP BY offer_presented_id, offer_presented, competitor_id, competitor_name
)
SELECT bo.*, o.price, o.monthly_cost, o.cost_type, o.base_save_rate, o.best_for
FROM by_offer_comp bo
LEFT JOIN bronze_retention_offers o ON bo.offer_id = o.offer_id;

-- Call topic analysis
CREATE OR REFRESH MATERIALIZED VIEW gold_call_topics AS
SELECT
  call_topic,
  COUNT(*)                                               AS call_volume,
  ROUND(AVG(is_saved), 4)                                AS save_rate,
  ROUND(AVG(is_churned), 4)                              AS churn_rate,
  ROUND(AVG(handle_time_min), 1)                         AS avg_handle_time_min,
  ROUND(AVG(CASE WHEN competitor_mentioned THEN 1 ELSE 0 END), 4) AS competitor_mention_rate,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)     AS pct_of_calls
FROM gold_call_interactions
GROUP BY call_topic;

-- Daily churn + competitor KPIs with rolling smoothing (the executive trend)
CREATE OR REFRESH MATERIALIZED VIEW gold_churn_metrics AS
WITH daily_calls AS (
  SELECT
    call_date,
    COUNT(*)                                                    AS total_calls,
    SUM(CASE WHEN competitor_mentioned THEN 1 ELSE 0 END)       AS competitor_mentions,
    SUM(is_saved)                                               AS saves,
    SUM(CASE WHEN call_topic IN ('Competitor Price Offer','Moving / Relocation','TV Value / Cord-Cutting')
             THEN 1 ELSE 0 END)                                 AS disconnect_intent_calls
  FROM gold_call_interactions
  GROUP BY call_date
),
daily_churn AS (
  SELECT CAST(churn_date AS DATE) AS d, COUNT(*) AS churned
  FROM bronze_customer_profiles
  WHERE status = 'Churned' AND churn_date IS NOT NULL
  GROUP BY CAST(churn_date AS DATE)
),
joined AS (
  SELECT
    dc.call_date,
    dc.total_calls, dc.competitor_mentions, dc.saves, dc.disconnect_intent_calls,
    COALESCE(ch.churned, 0) AS churned
  FROM daily_calls dc
  LEFT JOIN daily_churn ch ON dc.call_date = ch.d
),
windowed AS (
  SELECT
    call_date,
    total_calls,
    competitor_mentions,
    saves,
    disconnect_intent_calls,
    churned,
    -- 7-day smoothed competitor mention rate (28% -> 58%)
    ROUND(
      SUM(competitor_mentions) OVER (ORDER BY call_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
      / NULLIF(SUM(total_calls) OVER (ORDER BY call_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0)
    , 4)                                                          AS competitor_mention_rate,
    -- 7-day smoothed save rate
    ROUND(
      SUM(saves) OVER (ORDER BY call_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
      / NULLIF(SUM(total_calls) OVER (ORDER BY call_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0)
    , 4)                                                          AS save_rate,
    -- 30-day trailing monthlyized churn rate (1.8% -> 2.4%); base normalized to 51,600
    ROUND(
      100.0 * SUM(churned) OVER (ORDER BY call_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) / 51600.0
    , 3)                                                          AS churn_rate_pct
  FROM joined
)
-- trim the 30-day rolling warm-up so the executive chart opens at the ~1.8% baseline
SELECT * FROM windowed WHERE call_date >= DATE '2026-04-25' ORDER BY call_date;
