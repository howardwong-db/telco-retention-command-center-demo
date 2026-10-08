# Talk Track — TelcoABC Retention Command Center

Presenter guide. The app has 4 tabs: **Executive Dashboard**, **AI Assistant** (MAS chat), **Competitor Intelligence**, **Agent Coaching**. The timeline is live (the churn spike peaks ~3 weeks before "today," not at the chart edge).

## The hook (30 seconds)

> "A stable 1.8% monthly churn rate suddenly jumps to 2.4% — that's roughly 190,000 customers and about $180M of annualized revenue at risk. The cause: three competitors moved at once. This command center lets a retention supervisor see it, understand it, and act on it in real time — arming every agent with the right offer and the right words on every call. And it's all one Databricks platform: synthetic data, a declarative pipeline, an ML model, Genie, a RAG Knowledge Assistant, a multi-agent supervisor, an AI/BI dashboard, and a production app."

## The numbers (keep these exact)

| Metric | Value |
|---|---|
| Baseline → peak monthly churn | 1.8% → ~2.4% (peak ~3 weeks before today) |
| Competitor mentions on calls | 28% → 58% |
| Competitor share | T-Mobile ~38% · AT&T 24% · Verizon 5G 12% · Frontier 11% · Google 8% · Fios 7% |
| Agent tiers | 67 Top (avg 61% save) · 122 On-Target (48%) · 53 Needs-Coaching (37%) · 8 At-Risk (27%) |
| ROI | 5.3x — $52M revenue protected vs $8.2M cost |
| Top offer | TelcoABC One Bundle $49.99 (65.9% overall save) |
| T-Mobile framing insight | reliability-first = 68% save vs 35% for price-matching alone |
| Data scale | 120k calls · 250 agents · 50k scored customers · 6,380 Critical-tier · 10 call topics |
| Churn model | Gradient Boosted Trees, test AUC 0.892 |

## Demo flow (4 acts)

### Act 1 — Executive Dashboard: the problem
"Here's the alarm. Monthly churn spiking from 1.8% to 2.4%, competitor mentions doubling from 28% to 58%, and the inflection is clearly visible about three weeks ago. The ROI tile already frames the prize: a 5.3x return on the retention play, $52M protected."
- *Technical proof point:* medallion architecture, Auto Loader ingestion from a UC Volume, re-runnable on every new data drop.

### Act 2 — Competitor Intelligence: who's hitting us
"Every competitor has a ready-to-use talk track. T-Mobile Home Internet is 38% of our competitive mentions — the card shows its pricing, its real weaknesses (speed variability, peak-hour congestion, weather sensitivity, no TV bundle), and exactly how to counter it."
- *Technical proof point:* this content is RAG — a Knowledge Assistant over playbook docs, governed in Unity Catalog.

### Act 3 — Agent Coaching: who needs help and why
"Now I can see which of my 250 agents need help and why. The insight that matters: agents who lead with speed-reliability data hit a 68% save rate; those who price-match alone hit 35%. That's a coachable, measurable behavior — and the scatter plus the lowest-20 table tell me exactly where to spend coaching time."
- *Technical proof point:* a real MLflow-tracked model (AUC 0.892), calibrated risk tiers, not a mocked score.

### Act 4 — AI Assistant: the platform payoff
Type these live:
1. **Analytics (routes to Genie):** *"What's our current churn rate versus baseline?"*
2. **Playbook (routes to the Knowledge Assistant):** *"What's the best retention offer against T-Mobile Home Internet, and why?"*
3. **Combined (shows synthesis):** *"Which agents need coaching, and what should they say on T-Mobile calls?"*

"Notice the assistant answers with both the recommended offer AND the live data — the TelcoABC One Bundle, its actual save rate, and the reliability-first talk track. That's a Multi-Agent Supervisor routing to a Genie space for the numbers and a Knowledge Assistant for the playbook, then synthesizing one answer. And it runs each tool as the calling user, so governance is enforced consistently."

## The "so what" (close)

> "Everything here is one Databricks platform — no stitching together five vendors. The exact same pattern extends to upsell, cross-sell, and collections. You saw the problem, the diagnosis, and the action, with the ROI already quantified."
