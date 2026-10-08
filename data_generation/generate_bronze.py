"""
TelcoABC Retention Command Center — deterministic synthetic BRONZE data generator.

Lands 6 raw source datasets as JSON into the UC landing volume so a Spark
Declarative Pipeline can ingest them (Volume -> Bronze -> Gold).

Design targets (so dashboard charts land):
  - Monthly churn 1.8% baseline -> 2.4% peak ~3 weeks before today
  - Competitor mention rate 28% -> 58% over the same window
  - Competitor mention share: T-Mobile 38, AT&T 24, Verizon5G 12, Frontier 11, Google 8, VzFios 7
  - Agents: 67 Top(61%), 122 On Target(48%), 53 Needs Coaching(37%), 8 At Risk(27%)
  - Call volume +35% surge during the 2-week spike window
Deterministic: fixed numpy + Faker seeds.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker
from databricks.connect import DatabricksSession

# ----------------------------------------------------------------------------
# Set via env, or edit these for your workspace. PROFILE is your CLI profile.
import os
PROFILE = os.environ.get("DATABRICKS_PROFILE", "DEFAULT")
CATALOG = os.environ.get("TELCOABC_CATALOG", "main")
SCHEMA = os.environ.get("TELCOABC_SCHEMA", "telcoabc_retention")
LANDING = f"/Volumes/{CATALOG}/{SCHEMA}/landing"

SEED = 42
np.random.seed(SEED)
fake = Faker("en_US")
Faker.seed(SEED)

N_CUSTOMERS = 50_000
N_CALLS = 120_000
N_AGENTS = 250
N_SERVICE_EVENTS = 35_000

DAYS = 150
END_DATE = datetime(2026, 8, 22)              # chart edge = today
START_DATE = END_DATE - timedelta(days=DAYS - 1)
PEAK_DAY = DAYS - 22                            # spike peak ~3 weeks before edge
SPIKE_LO, SPIKE_HI = PEAK_DAY - 10, PEAK_DAY + 4  # ~2-week surge window

spark = DatabricksSession.builder.profile(PROFILE).serverless(True).getOrCreate()

def day_to_date(d):
    return START_DATE + timedelta(days=int(d))

# temporal "bump": 0 at baseline, 1 at the peak (gaussian around PEAK_DAY)
def bump(days_arr):
    return np.exp(-0.5 * ((days_arr - PEAK_DAY) / 12.0) ** 2)

def write_json(pdf, name):
    sdf = spark.createDataFrame(pdf)
    (sdf.coalesce(4).write.mode("overwrite")
        .json(f"{LANDING}/{name}"))
    print(f"  landed {name}: {len(pdf):,} rows -> {LANDING}/{name}")

# ============================================================================
# 1. COMPETITOR INTEL (6)  — reference dim
# ============================================================================
competitors = [
    ("COMP-01", "T-Mobile Home Internet", 0.38, "$50/mo flat, 5G FWA",
     "Speed 33-245 Mbps (~100 avg), peak-hour congestion, weather-dependent, no TV bundle",
     "OFF-01", "Lead with speed-reliability data (consistent wired speeds vs variable 5G), then the TelcoABC One bundle at $49.99."),
    ("COMP-02", "AT&T Fiber", 0.24, "$30-80/mo, up to 5 Gbps",
     "Promo expires after 12mo (+$25-35), equipment fees, many addresses get Internet Air FWA not fiber, no mobile bundle",
     "OFF-03", "Expose the post-promo price jump; lock in a 12-month price guarantee now."),
    ("COMP-03", "Verizon 5G Home", 0.12, "$25-35/mo but requires Verizon mobile ($65-90/line); combined $90-115/mo",
     "Only cheap if you already pay for Verizon mobile; true combined cost is high",
     "OFF-01", "Do the real math on combined cost; the TelcoABC One bundle beats it outright."),
    ("COMP-04", "Frontier Fiber", 0.11, "$45-75/mo fiber, limited footprint",
     "Spotty availability, install delays, weaker TV/mobile story",
     "OFF-04", "Emphasize immediate availability and free speed upgrade."),
    ("COMP-05", "Google Fiber", 0.08, "$70-100/mo, ~20 metros, no TV/mobile",
     "Expensive, metro-only, no TV or mobile bundle",
     "OFF-01", "Bundle value vs standalone premium price — TelcoABC One at $49.99."),
    ("COMP-06", "Verizon Fios", 0.07, "$50-90/mo fiber, East Coast only, no integrated TV",
     "Regional, pricey, no integrated TV package",
     "OFF-01", "TelcoABC One / Triple Play total-value comparison."),
]
comp_pdf = pd.DataFrame(competitors, columns=[
    "competitor_id", "competitor_name", "mention_share", "pricing",
    "weaknesses", "best_counter_offer_id", "talk_track"])
write_json(comp_pdf, "competitor_intel")
COMP_IDS = comp_pdf["competitor_id"].tolist()
COMP_SHARE = comp_pdf["mention_share"].to_numpy()
COMP_SHARE = COMP_SHARE / COMP_SHARE.sum()

# ============================================================================
# 2. RETENTION OFFERS (7)  — reference dim
# ============================================================================
offers = [
    ("OFF-01", "TelcoABC One Bundle $49.99", 49.99, 15.00, 0.68, "monthly",
     "Internet-only customers citing competitor pricing"),
    ("OFF-02", "Mobile Line Free 12mo", 0.00, 29.99, 0.61, "monthly",
     "Customers not yet on TelcoABC Mobile"),
    ("OFF-03", "12-Month Price Lock", 0.00, 8.00, 0.52, "deferred",
     "Customers worried about rate increases / promo expiration"),
    ("OFF-04", "Free Upgrade to Ultra", 0.00, 12.00, 0.48, "monthly",
     "Speed complainers / fiber comparisons"),
    ("OFF-05", "Loyalty Credit $15/mo", 0.00, 15.00, 0.45, "monthly",
     "Long-tenure customers feeling undervalued"),
    ("OFF-06", "$100 Bill Credit", 0.00, 100.00, 0.35, "one-time",
     "Billing disputes"),
    ("OFF-07", "Free Premium Channels 6mo", 0.00, 0.00, 0.32, "minimal",
     "TV customers considering cord-cutting"),
]
offer_pdf = pd.DataFrame(offers, columns=[
    "offer_id", "offer_name", "price", "monthly_cost", "base_save_rate",
    "cost_type", "best_for"])
write_json(offer_pdf, "retention_offers")
OFFER_SAVE = dict(zip(offer_pdf.offer_id, offer_pdf.base_save_rate))

# ============================================================================
# 3. AGENTS (250)  — with tier baselines
# ============================================================================
tier_spec = [  # (tier, count, save_rate, handle_time_min, nps)
    ("Top Performer", 67, 0.61, 9.5, 62),
    ("On Target", 122, 0.48, 12.0, 41),
    ("Needs Coaching", 53, 0.37, 15.5, 24),
    ("At Risk", 8, 0.27, 18.5, 9),
]
rows, aid = [], 1
teams = [f"Team {c}" for c in "ABCDEFGHIJ"]
for tier, cnt, sr, ht, nps in tier_spec:
    for _ in range(cnt):
        rows.append((
            f"AGT-{aid:04d}", fake.name(), teams[aid % len(teams)], tier,
            round(float(np.clip(np.random.normal(sr, 0.03), 0.05, 0.95)), 3),
            round(float(np.clip(np.random.normal(ht, 1.5), 4, 30)), 1),
            int(np.clip(np.random.normal(nps, 6), -30, 90)),
            (END_DATE - timedelta(days=int(np.random.uniform(120, 2200)))).date().isoformat(),
        ))
        aid += 1
agent_pdf = pd.DataFrame(rows, columns=[
    "agent_id", "agent_name", "team", "tier",
    "baseline_save_rate", "avg_handle_time_min", "nps", "hire_date"])
write_json(agent_pdf, "agents")
AGENT_IDS = agent_pdf.agent_id.to_numpy()
AGENT_SAVE = dict(zip(agent_pdf.agent_id, agent_pdf.baseline_save_rate))

# ============================================================================
# 4. CUSTOMER PROFILES (50,000)  — with churn status/date following the curve
# ============================================================================
markets = ["Los Angeles", "New York", "Dallas", "Charlotte", "Tampa", "St. Louis",
           "Columbus", "Austin", "Denver", "Kansas City", "Cincinnati", "Milwaukee"]
market_comp_intensity = np.random.uniform(0.4, 1.0, len(markets))  # competitor pressure per market

plan_types = np.random.choice(
    ["Internet Only", "Internet + Mobile", "Double Play (Internet+TV)", "Triple Play"],
    N_CUSTOMERS, p=[0.42, 0.20, 0.23, 0.15])
has_mobile = np.isin(plan_types, ["Internet + Mobile", "Triple Play"])
tenure = np.clip(np.random.exponential(34, N_CUSTOMERS), 1, 240).astype(int)
monthly_spend = np.round(np.clip(
    np.where(plan_types == "Internet Only", np.random.lognormal(4.25, 0.35, N_CUSTOMERS),
    np.where(plan_types == "Internet + Mobile", np.random.lognormal(4.75, 0.35, N_CUSTOMERS),
    np.where(plan_types == "Double Play (Internet+TV)", np.random.lognormal(4.85, 0.35, N_CUSTOMERS),
             np.random.lognormal(5.15, 0.35, N_CUSTOMERS)))), 25, 400), 2)
mkt_idx = np.random.randint(0, len(markets), N_CUSTOMERS)
speed_tier = np.random.choice(["100 Mbps", "300 Mbps", "500 Mbps", "1 Gbps"],
                              N_CUSTOMERS, p=[0.30, 0.38, 0.20, 0.12])
contract = np.random.choice(["Month-to-Month", "1-Year", "2-Year"], N_CUSTOMERS, p=[0.55, 0.30, 0.15])
autopay = np.random.rand(N_CUSTOMERS) < 0.62
signup = np.array([(END_DATE - timedelta(days=int(t * 30 + np.random.uniform(0, 25)))).date().isoformat()
                   for t in tenure])

# churn propensity (used only to CHOOSE who churns; not written as a score)
prop = (0.9 * (plan_types == "Internet Only")
        + 0.7 * (~has_mobile)
        + 0.8 * (contract == "Month-to-Month")
        + 0.6 * market_comp_intensity[mkt_idx]
        + 0.5 * (tenure < 12)
        + 0.4 * (monthly_spend > 120)
        + np.random.normal(0, 0.4, N_CUSTOMERS))
# pick ~5,050 churners over the window (=> ~1.9% avg monthly on 50k)
N_CHURN = 5050
churn_idx = np.argsort(-prop)[:N_CHURN + 4000]           # candidate pool
churn_idx = np.random.choice(churn_idx, N_CHURN, replace=False)
# distribute churn dates by the temporal bump (more near the spike)
day_weights = 1.0 + 0.42 * bump(np.arange(DAYS))         # softened so smoothed peak ~+33%
day_weights /= day_weights.sum()
churn_days = np.random.choice(np.arange(DAYS), N_CHURN, p=day_weights)
status = np.array(["Active"] * N_CUSTOMERS, dtype=object)
churn_date = np.array([None] * N_CUSTOMERS, dtype=object)
status[churn_idx] = "Churned"
for i, d in zip(churn_idx, churn_days):
    churn_date[i] = day_to_date(d).date().isoformat()

cust_pdf = pd.DataFrame({
    "customer_id": [f"CUST-{i:06d}" for i in range(N_CUSTOMERS)],
    "customer_name": [fake.name() for _ in range(N_CUSTOMERS)],
    "market": [markets[i] for i in mkt_idx],
    "plan_type": plan_types,
    "has_mobile": has_mobile,
    "internet_speed": speed_tier,
    "tenure_months": tenure,
    "monthly_spend": monthly_spend,
    "contract_type": contract,
    "autopay_enrolled": autopay,
    "signup_date": signup,
    "status": status,
    "churn_date": churn_date,
})
write_json(cust_pdf, "customer_profiles")
CUST_IDS = cust_pdf.customer_id.to_numpy()
# per-customer competitor pressure for call generation
CUST_PRESSURE = market_comp_intensity[mkt_idx]

# ============================================================================
# 5. SERVICE EVENTS (35,000)
# ============================================================================
ev_cust = np.random.choice(N_CUSTOMERS, N_SERVICE_EVENTS,
                           p=(prop - prop.min() + 0.1) / (prop - prop.min() + 0.1).sum())
ev_days = np.random.choice(np.arange(DAYS), N_SERVICE_EVENTS,
                           p=(1.0 + 0.4 * bump(np.arange(DAYS))) / (1.0 + 0.4 * bump(np.arange(DAYS))).sum())
ev_type = np.random.choice(
    ["Outage", "Slow Speed", "Install/Activation", "Scheduled Maintenance", "Billing System"],
    N_SERVICE_EVENTS, p=[0.30, 0.28, 0.18, 0.14, 0.10])
ev_sev = np.where(np.isin(ev_type, ["Outage", "Slow Speed"]),
                  np.random.choice(["High", "Medium", "Low"], N_SERVICE_EVENTS, p=[0.4, 0.4, 0.2]),
                  np.random.choice(["High", "Medium", "Low"], N_SERVICE_EVENTS, p=[0.1, 0.4, 0.5]))
svc_pdf = pd.DataFrame({
    "event_id": [f"SVC-{i:07d}" for i in range(N_SERVICE_EVENTS)],
    "customer_id": CUST_IDS[ev_cust],
    "event_type": ev_type,
    "severity": ev_sev,
    "event_date": [day_to_date(d).date().isoformat() for d in ev_days],
    "duration_min": np.round(np.clip(np.random.exponential(45, N_SERVICE_EVENTS), 1, 1440), 0).astype(int),
    "market": [markets[i] for i in mkt_idx[ev_cust]],
})
write_json(svc_pdf, "service_events")

# ============================================================================
# 6. CALL INTERACTIONS (120,000)  — the fact table
# ============================================================================
# sample call dates with a +35% surge in the spike window
base_vol = np.ones(DAYS)
base_vol[SPIKE_LO:SPIKE_HI] *= 1.35
base_vol = base_vol / base_vol.sum()
call_days = np.random.choice(np.arange(DAYS), N_CALLS, p=base_vol)

# competitor mention prob rises 28% -> 58% following the bump
p_mention = 0.28 + 0.30 * bump(call_days)
mentioned = np.random.rand(N_CALLS) < p_mention
comp_choice = np.where(mentioned,
                       COMP_IDS_arr := np.array(COMP_IDS)[np.random.choice(len(COMP_IDS), N_CALLS, p=COMP_SHARE)],
                       None)

call_cust = np.random.randint(0, N_CUSTOMERS, N_CALLS)
call_agent = AGENT_IDS[np.random.randint(0, N_AGENTS, N_CALLS)]

# call topic (enumerated) — correlated with mention / competitor
TOPICS = ["Competitor Price Offer", "Rate Increase Concern", "Billing Dispute",
          "Slow Speed / Performance", "Outage / Reliability", "Promo / Contract Expiration",
          "Moving / Relocation", "TV Value / Cord-Cutting", "Mobile / Bundle Interest",
          "Loyalty / Feels Undervalued"]
topic = np.empty(N_CALLS, dtype=object)
rand_t = np.random.rand(N_CALLS)
for i in range(N_CALLS):
    if mentioned[i]:
        c = comp_choice[i]
        if c in ("COMP-01", "COMP-03", "COMP-05", "COMP-06"):        # price-led competitors
            topic[i] = "Competitor Price Offer" if rand_t[i] < 0.6 else "Slow Speed / Performance"
        elif c == "COMP-02":                                          # AT&T promo/fiber
            topic[i] = "Promo / Contract Expiration" if rand_t[i] < 0.5 else "Slow Speed / Performance"
        else:                                                         # Frontier
            topic[i] = "Slow Speed / Performance" if rand_t[i] < 0.5 else "Competitor Price Offer"
    else:
        topic[i] = np.random.choice(
            ["Rate Increase Concern", "Billing Dispute", "Slow Speed / Performance",
             "Outage / Reliability", "Moving / Relocation", "TV Value / Cord-Cutting",
             "Mobile / Bundle Interest", "Loyalty / Feels Undervalued"],
            p=[0.17, 0.15, 0.12, 0.10, 0.10, 0.12, 0.10, 0.14])

# recommended/presented offer: best counter for the competitor, else topic-based
comp_counter = dict(zip(comp_pdf.competitor_id, comp_pdf.best_counter_offer_id))
topic_offer = {
    "Competitor Price Offer": "OFF-01", "Rate Increase Concern": "OFF-03",
    "Billing Dispute": "OFF-06", "Slow Speed / Performance": "OFF-04",
    "Outage / Reliability": "OFF-04", "Promo / Contract Expiration": "OFF-03",
    "Moving / Relocation": "OFF-05", "TV Value / Cord-Cutting": "OFF-07",
    "Mobile / Bundle Interest": "OFF-02", "Loyalty / Feels Undervalued": "OFF-05"}
offer_presented = np.array([comp_counter[comp_choice[i]] if mentioned[i] else topic_offer[topic[i]]
                            for i in range(N_CALLS)], dtype=object)

# outcome: save probability tracks the AGENT'S skill, modulated by offer quality and
# time drag during the surge (keeps tier save rates ~61/48/37/27 visible)
agent_sr = np.array([AGENT_SAVE[a] for a in call_agent])
offer_sr = np.array([OFFER_SAVE[o] for o in offer_presented])
time_drag = 1.0 - 0.12 * bump(call_days)                  # harder to save during the surge
p_save = np.clip(agent_sr * (offer_sr / 0.48) * time_drag, 0.03, 0.97)
saved = np.random.rand(N_CALLS) < p_save
offer_accepted = saved & (np.random.rand(N_CALLS) < 0.92)
outcome = np.where(saved, "Saved", np.where(np.random.rand(N_CALLS) < 0.55, "Churned", "Pending"))

# handle time (min) — tied to agent baseline + topic complexity
agent_ht = dict(zip(agent_pdf.agent_id, agent_pdf.avg_handle_time_min))
base_ht = np.array([agent_ht[a] for a in call_agent])
handle_min = np.round(np.clip(base_ht + np.random.normal(0, 2.5, N_CALLS)
                              + np.where(mentioned, 2.0, 0.0), 3, 45), 1)

# raw customer mention text (for ai_classify showcase + realism)
snippets = {
    "Competitor Price Offer": ["T-Mobile is offering me {price} flat, why am I paying so much",
                               "saw a {comp} deal for way less than my bill"],
    "Rate Increase Concern": ["my bill went up again and I want to know why",
                              "promo ended and the price jumped"],
    "Billing Dispute": ["I was charged twice this month", "there's a fee I don't recognize"],
    "Slow Speed / Performance": ["my internet is so slow in the evenings",
                                 "speeds are nothing like what I pay for"],
    "Outage / Reliability": ["service keeps dropping every day", "third outage this month"],
    "Promo / Contract Expiration": ["my contract is ending and AT&T offered free install",
                                    "the intro price is expiring next month"],
    "Moving / Relocation": ["I'm moving and not sure you cover my new address",
                            "relocating next month, need to transfer or cancel"],
    "TV Value / Cord-Cutting": ["thinking of dropping TV, I just stream now",
                                "cable package is too expensive for what I watch"],
    "Mobile / Bundle Interest": ["do you have a mobile plan that bundles with internet",
                                 "interested in adding a phone line"],
    "Loyalty / Feels Undervalued": ["I've been a customer 10 years and get nothing",
                                    "new customers get better deals than me"],
}
comp_name_map = dict(zip(comp_pdf.competitor_id, comp_pdf.competitor_name))
def mk_text(i):
    t = topic[i]
    s = snippets[t][i % len(snippets[t])]
    return s.format(price="$50/mo",
                    comp=comp_name_map.get(comp_choice[i], "a competitor"))
mention_text = [mk_text(i) for i in range(N_CALLS)]

call_pdf = pd.DataFrame({
    "call_id": [f"CALL-{i:07d}" for i in range(N_CALLS)],
    "customer_id": CUST_IDS[call_cust],
    "agent_id": call_agent,
    "call_date": [day_to_date(d).date().isoformat() for d in call_days],
    "handle_time_min": handle_min,
    "competitor_mentioned": mentioned,
    "competitor_id": comp_choice,
    "call_topic": topic,
    "mention_text": mention_text,
    "offer_presented_id": offer_presented,
    "offer_accepted": offer_accepted,
    "outcome": outcome,
})
write_json(call_pdf, "call_interactions")

print("\nDONE. Landed 6 bronze sources into", LANDING)
print("Quick checks:")
print("  overall mention rate:", round(mentioned.mean(), 3))
print("  spike-window mention rate:",
      round(mentioned[np.isin(call_days, np.arange(SPIKE_LO, SPIKE_HI))].mean(), 3))
print("  baseline-window mention rate:",
      round(mentioned[call_days < 20].mean(), 3))
print("  overall save rate:", round(saved.mean(), 3))
print("  churned customers:", int((status == "Churned").sum()))
