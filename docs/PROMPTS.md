# Prompts & AI Configuration

Two parts:
- **Part A — Demo AI prompts/instructions** wired into the running demo (Genie, Knowledge Assistant, MAS, `ai_classify`), so you can rebuild the agents.
- **Part B — The one-shot build prompt** used to generate the whole demo via the Databricks Solution Builder / one-shot-demo workflow.

Substitute `<CATALOG>` / `<SCHEMA>` with your target catalog/schema throughout.

---

## Part A — Demo AI prompts

### Genie space — "TelcoABC Retention Analytics"

Full config: `agent_bricks/genie_agent.json`. It reads 6 gold tables: `gold_agent_performance`, `gold_call_interactions`, `gold_call_topics`, `gold_churn_metrics`, `gold_churn_risk_scores`, `gold_retention_offers`.

**Text instructions (the system prompt):**

> You are the analytics agent for the TelcoABC Retention Command Center. You answer questions about customer churn, retention-call outcomes, competitor pressure, agent coaching, and retention-offer effectiveness for TelcoABC.
>
> Table guide: `gold_churn_metrics` = daily KPI trend (churn_rate_pct, competitor_mention_rate, save_rate) — use for 'trend', 'spike', 'baseline vs peak' questions. `gold_call_interactions` = one row per retention call (competitor_mentioned, competitor_name, call_topic, outcome, is_saved, offer_presented, agent) — use for volume, topic, and competitor-share questions. `gold_churn_risk_scores` = one row per customer (churn_score, risk_tier, recommended_offer_id) — use for at-risk counts and Critical-tier analysis; risk tiers are Critical (>=0.55), High, Medium, Low. `gold_agent_performance` = one row per agent (save_rate, tier, avg_handle_time_min, offer_conversion_rate, save_rate_rank) — use for coaching questions; tiers are Top Performer, On Target, Needs Coaching, At Risk. `gold_retention_offers` = offer effectiveness by competitor (save_rate, times_presented). `gold_call_topics` = call volume and save rate by topic.
>
> Business context: baseline monthly churn is ~1.8%, peaked ~2.4% during the recent competitor surge. Competitor mention rate rose from ~28% to ~58%. The TelcoABC One Bundle is the strongest counter-offer to T-Mobile Home Internet.
>
> When asked about 'coaching' or 'underperformers', focus on agents in the Needs Coaching and At Risk tiers. When asked about 'the spike' or 'recent surge', reference the peak in `gold_churn_metrics`. Always present rates as percentages rounded to one decimal.

**Sample questions:**
1. What is our current monthly churn rate and how does it compare to the baseline?
2. Which competitor is mentioned most often on retention calls?
3. How many Critical-tier customers do we have and what is their average churn risk score?
4. Which agents need coaching based on save rate?
5. What are the most common call topics and which have the lowest save rate?
6. What is the save rate for the TelcoABC One Bundle against T-Mobile Home Internet?

**Example-question SQL** (teaches Genie the join patterns; full text in the JSON):
- Churn vs baseline → `MIN/MAX(churn_rate_pct)` on `gold_churn_metrics`
- Competitor share → `COUNT(*)` + window `%` on `gold_call_interactions WHERE competitor_mentioned`
- Critical count → `COUNT(*)`, `AVG(churn_score)` on `gold_churn_risk_scores WHERE risk_tier='Critical'`
- Coaching list → `gold_agent_performance WHERE tier IN ('Needs Coaching','At Risk') ORDER BY save_rate ASC`
- Best offer vs T-Mobile → `gold_retention_offers WHERE competitor_name='T-Mobile Home Internet' ORDER BY save_rate DESC`

### Knowledge Assistant — "TelcoABC Retention Playbooks"

RAG over the 5 markdown docs in `agent_bricks/playbooks/`:
- `01_tmobile_home_internet_playbook.md` — T-Mobile positioning, weaknesses (speed variability, peak congestion, weather, no TV bundle), best counter = TelcoABC One Bundle (~68% save), reliability-first talk track.
- `02_att_fiber_playbook.md` — AT&T Fiber promo cliff, equipment fees, Internet Air FWA; best counter = 12-Month Price Lock (~52%).
- `03_verizon_and_others_playbook.md` — Verizon 5G Home, Verizon Fios, Frontier Fiber, Google Fiber positioning + counter-offers.
- `04_coaching_guide.md` — the coachable insight: reliability-framing agents save ~68% vs ~35% for price-matching alone.
- `05_retention_offer_catalog.md` — 7 offers with save rate, monthly cost, and ideal use case.

**Role:** given a competitor or situation, return the specific counter-offer, the competitor's weaknesses, and a ready-to-use talk track.

### Multi-Agent Supervisor — "TelcoABC Retention Assistant"

**Routing instruction:**

> Route analytics / metric / "how many / what rate / which agents" questions to the **Genie space** (TelcoABC Retention Analytics). Route "what offer / how do I handle / talk track / competitor weakness" questions to the **Knowledge Assistant** (TelcoABC Retention Playbooks). When a question needs both (e.g. "best offer against T-Mobile and does the data back it up"), call both tools and synthesize a single answer that combines the recommended offer and talk track with the supporting numbers.

**Identity / governance:** the MAS executes each downstream tool **as the calling identity** (the app's service principal). The SP must have direct access to each tool (Genie `CAN_RUN`, KA endpoint `CAN_QUERY`), not just the MAS endpoint. See the README gotcha.

### `ai_classify` — call-topic labeling

In `notebooks/01_data_ingestion_showcase.py`, raw unlabeled call mentions are auto-labeled into one of 10 enumerated topics:

```sql
ai_classify(
  mention_text,
  ARRAY(
    'Competitor Price Offer', 'Rate Increase Concern', 'Billing Dispute',
    'Slow Speed / Performance', 'Outage / Reliability', 'Promo / Contract Expiration',
    'Moving / Relocation', 'TV Value / Cord-Cutting', 'Mobile / Bundle Interest',
    'Loyalty / Feels Undervalued'
  )
) AS ai_call_topic
```

This turns free-text customer language into governed topic labels that feed `gold_call_topics`, the Genie space, and the dashboard — no manual tagging.

---

## Part B — One-shot build prompt

Paste into the Databricks Solution Builder (one-shot-demo). Replace the deploy target with your own workspace/catalog/schema.

> Build a Call Center Churn & Retention Prevention demo for TelcoABC, telecom/cable industry — a "Retention Command Center" that equips 2,500+ retention agents with real-time churn risk scores, competitor talk tracks, and AI-recommended retention offers.
>
> **Deploy target:** my `<your-workspace>` workspace, catalog `<CATALOG>`, schema `<SCHEMA>`. Start with synthetic data. **Show me the story for approval before building.**
>
> **Story.** Protagonist: a TelcoABC call-center retention supervisor and her 250 agents. Baseline monthly churn is a stable 1.8%. Catalyst (make it visible in the dashboards, peaking ~3 weeks before today, not at the chart edge): three competitor moves hit at once — T-Mobile launched a $50/mo flat-rate 5G home internet promo, AT&T ran free-fiber-install campaigns in 8 overlap markets, and Verizon bundled 5G Home with mobile discounts. Disconnect call volume surged 35% in two weeks; monthly churn spiked 1.8% → 2.4% (+33%); competitor mention rate on calls jumped 28% → 58%. Without action: ~190,000 customers lost = $180M annualized Q1 revenue at risk.
>
> Journey: the supervisor opens the Executive Dashboard and sees the churn spike + competitor-mention surge → asks an AI assistant (backed by a Knowledge Assistant of competitive playbooks/talk tracks) "what retention offer works best against T-Mobile Home Internet?" and gets a specific, data-backed answer → drills into Agent Coaching to see which agents need coaching and why (offer conversion, handle time, save rate) → reviews the Critical-tier customer list where each customer has a recommended offer.
>
> Resolution: deploying the TelcoABC One counter-offer to agents handling T-Mobile calls lifts save rate 42% → 54%, retaining ~23,000 customers in Q1 = $52M protected vs $8.2M cost = 5.3x ROI, 28% churn reduction.
>
> **Capabilities to showcase:** synthetic data generation; a Lakeflow / Spark Declarative Pipeline (bronze → gold medallion); an AI/BI dashboard (published Executive "Retention Command Center" view); a Genie Space ("TelcoABC Retention Analytics"); a Knowledge Assistant ("TelcoABC Retention Playbooks") loaded with competitor playbooks + talk tracks + coaching guides; ML churn scoring (risk score per customer); and a Databricks App (multi-tab "TelcoABC Retention Command Center": Executive Dashboard, AI Assistant, Competitor Intelligence, Agent Coaching). Add a Multi-Agent Supervisor that routes the AI Assistant across the Genie Space and the Knowledge Assistant.
>
> **Synthetic data model.** Bronze: bronze_customer_profiles (50,000 customers — plans, tenure, monthly spend); bronze_call_interactions (120,000 retention call logs — outcomes, competitor mentions, and a call_topic label plus raw mention text); bronze_agents (250 agents with performance baselines); bronze_service_events (35,000 network outages / service events); bronze_competitor_intel (6 competitors — pricing, weaknesses, talk tracks); bronze_retention_offers (7 offers with historical save rates). Gold: gold_churn_risk_scores (50,000 ML scores; Critical tier ~6,375, avg ~0.665); gold_call_interactions (120,000 enriched calls with churn/competitor flags); gold_agent_performance (250 agents with coaching metrics + peer rankings — tiers: 67 Top Performers @61% save, 122 On Target @48%, 53 Needs Coaching @37%, 8 At Risk @27%); gold_retention_offers (offer effectiveness by competitor); gold_call_topics (call volume, save rate, churn rate by topic); gold_churn_metrics (~150 daily KPI rows showing the spike).
>
> **Call topic labeling:** enumerate ~10 call topics derived from customer mentions (Competitor Price Offer, Rate Increase Concern, Billing Dispute, Slow Speed / Performance, Outage / Reliability, Promo / Contract Expiration, Moving / Relocation, TV Value / Cord-Cutting, Mobile / Bundle Interest, Loyalty / Feels Undervalued) and aggregate them into gold_call_topics for topic analytics.
>
> **Key numbers the data must reproduce (so charts land):** churn 1.8% baseline → 2.4% peak; competitor mentions 28% → 58%; competitor mention share — T-Mobile Home Internet 38%, AT&T Fiber 24%, Verizon 5G Home 12%, Frontier Fiber 11%, Google Fiber 8%, Verizon Fios 7%. Retention offers (offer / save rate / cost / best-for): TelcoABC One Bundle $49.99 / 68% / $15/mo / internet-only citing competitor pricing; Mobile Line Free 12mo / 61% / $29.99/mo / not yet on TelcoABC Mobile; 12-Month Price Lock / 52% / $8/mo deferred / worried about rate increases; Free Upgrade to Ultra / 48% / $12/mo / speed complainers; Loyalty Credit $15/mo / 45% / $15/mo / long-tenure feeling undervalued; $100 Bill Credit / 35% / $100 one-time / billing disputes; Free Premium Channels 6mo / 32% / minimal / TV cord-cutters.
>
> **Data ingestion showcase:** generate a notebook that lands a fresh sample-data drop into a Volume, shows the Spark Declarative Pipeline ingesting it to bronze, then re-runs the bronze → gold transforms; include an ai_classify example that auto-labels the free-text customer mention into a call topic.
>
> **Knowledge Assistant content (load as RAG docs):** T-Mobile Home Internet (38%) — $50/mo flat 5G FWA; weaknesses: speed 33–245 Mbps (~100 avg), peak-hour congestion, weather-dependent, no TV bundle; best counter TelcoABC One Bundle $49.99 (68%); talk track leads with speed-reliability data then the bundle. AT&T Fiber (24%) — $30–80/mo up to 5 Gbps; weaknesses: promo expires after 12mo (+$25–35), equipment fees, many addresses get Internet Air FWA not fiber, no mobile bundle; best counter 12-Month Price Lock (52%). Verizon 5G Home (12%) — $25–35/mo but requires Verizon mobile ($65–90/line), combined $90–115/mo; best counter TelcoABC One Bundle. Verizon Fios (7%) — $50–90/mo fiber, East Coast only, no integrated TV; best counter TelcoABC One / Triple Play. Frontier Fiber (11%) — limited footprint, install delays; best counter Free Upgrade to Ultra. Google Fiber (8%) — $70–100/mo, ~20 metros, no TV/mobile; best counter TelcoABC One Bundle. Also include an agent coaching guide (the 68%-vs-35% speed-reliability insight) and the retention offer catalog.
>
> **App tabs:** Executive Dashboard (churn-vs-save-rate trend with the inflection ~3 weeks before today, competitor-mentions pie, Critical-tier customer table with a recommended offer per customer, ROI/business-case tile); AI Assistant (chat backed by the MAS; returns offers + talk tracks + competitor weaknesses); Competitor Intelligence (expandable card per competitor with pricing, weaknesses, ready-to-use talk track); Agent Coaching (KPI cards by tier, save-rate-vs-handle-time scatter, lowest-20-agents coaching table, coaching insight text). Display the logged-in user's email and persist chat with Lakebase.
