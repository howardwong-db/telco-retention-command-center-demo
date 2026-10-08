"""TelcoABC Retention Command Center - FastAPI backend."""
import os

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from server import sql, mas, db
from server.config import FQ
from server.competitors import COMPETITOR_FACTS

app = FastAPI(title="TelcoABC Retention Command Center")

# ---------------------------------------------------------------- identity ---
DEV_EMAIL = os.environ.get("DEV_USER_EMAIL", "demo-user@example.com")


def get_identity(request: Request) -> tuple[str, str | None]:
    """Return (email, oauth_token) from Databricks Apps forwarded headers."""
    email = request.headers.get("x-forwarded-email") or DEV_EMAIL
    token = request.headers.get("x-forwarded-access-token") or os.environ.get("DEV_DB_TOKEN")
    return email, token


@app.get("/api/me")
async def me(request: Request):
    email, token = get_identity(request)
    return {"email": email, "authenticated": bool(request.headers.get("x-forwarded-email"))}


# =============================================================== DASHBOARD ===
@app.get("/api/dashboard")
async def dashboard():
    metrics = sql.run_query(
        f"""SELECT CAST(call_date AS STRING) call_date,
                   CAST(churn_rate_pct AS DOUBLE) churn_rate_pct,
                   CAST(competitor_mention_rate AS DOUBLE) competitor_mention_rate,
                   CAST(save_rate AS DOUBLE) save_rate
            FROM {FQ}.gold_churn_metrics ORDER BY call_date"""
    )
    latest = metrics[-1] if metrics else {}

    critical_count = sql.run_query(
        f"SELECT COUNT(*) c FROM {FQ}.gold_churn_risk_scores WHERE risk_tier = 'Critical'"
    )
    critical_n = int(sql.num(critical_count[0]["c"])) if critical_count else 0

    pie = sql.run_query(
        f"""SELECT competitor_name, COUNT(*) mentions
            FROM {FQ}.gold_call_interactions
            WHERE competitor_mentioned = true
            GROUP BY competitor_name ORDER BY mentions DESC"""
    )

    critical_customers = sql.run_query(
        f"""SELECT customer_id, market, plan_type,
                   CAST(monthly_spend AS DOUBLE) monthly_spend,
                   CAST(churn_score AS DOUBLE) churn_score,
                   recommended_offer_id
            FROM {FQ}.gold_churn_risk_scores
            WHERE risk_tier = 'Critical'
            ORDER BY churn_score DESC LIMIT 50"""
    )

    return {
        "kpis": {
            "churn_rate_pct": sql.num(latest.get("churn_rate_pct")),
            "competitor_mention_rate": sql.num(latest.get("competitor_mention_rate")),
            "critical_count": critical_n,
            "save_rate": sql.num(latest.get("save_rate")),
        },
        "trend": [
            {
                "call_date": m["call_date"],
                "churn_rate_pct": sql.num(m["churn_rate_pct"]),
                "competitor_mention_rate": sql.num(m["competitor_mention_rate"]) * 100,
            }
            for m in metrics
        ],
        "competitor_pie": [
            {"name": p["competitor_name"], "value": int(sql.num(p["mentions"]))} for p in pie
        ],
        "critical_customers": [
            {
                "customer_id": c["customer_id"],
                "market": c["market"],
                "plan_type": c["plan_type"],
                "monthly_spend": sql.num(c["monthly_spend"]),
                "churn_score": sql.num(c["churn_score"]),
                "recommended_offer_id": c["recommended_offer_id"],
            }
            for c in critical_customers
        ],
        "roi": {
            "multiple": 5.3,
            "protected_revenue_m": 52.0,
            "program_cost_m": 8.2,
            "churn_reduction_pct": 28,
        },
    }


# ============================================================== COMPETITORS ===
@app.get("/api/competitors")
async def competitors():
    offers = sql.run_query(
        f"""SELECT offer_id, offer_name,
                   CAST(save_rate AS DOUBLE) save_rate,
                   CAST(price AS DOUBLE) price,
                   CAST(monthly_cost AS DOUBLE) monthly_cost, best_for
            FROM {FQ}.gold_retention_offers"""
    )
    # Best (highest) save rate seen per offer_id
    offer_by_id: dict[str, dict] = {}
    for o in offers:
        oid = o["offer_id"]
        sr = sql.num(o["save_rate"])
        if oid not in offer_by_id or sr > offer_by_id[oid]["save_rate"]:
            offer_by_id[oid] = {
                "offer_id": oid,
                "offer_name": o["offer_name"],
                "save_rate": sr,
                "price": sql.num(o["price"]),
                "monthly_cost": sql.num(o["monthly_cost"]),
                "best_for": o["best_for"],
            }

    cards = []
    for f in COMPETITOR_FACTS:
        counter = offer_by_id.get(f["counter_offer_id"])
        cards.append({**f, "counter_offer": counter})
    return {"competitors": cards, "offers": list(offer_by_id.values())}


# ============================================================ AGENT COACHING ===
@app.get("/api/agents")
async def agents():
    tiers = sql.run_query(
        f"""SELECT tier, COUNT(*) agents,
                   AVG(save_rate) avg_save_rate,
                   AVG(avg_handle_time_min) avg_handle_time,
                   AVG(nps) avg_nps
            FROM {FQ}.gold_agent_performance GROUP BY tier"""
    )
    scatter = sql.run_query(
        f"""SELECT agent_name, team, tier,
                   CAST(save_rate AS DOUBLE) save_rate,
                   CAST(avg_handle_time_min AS DOUBLE) avg_handle_time_min,
                   CAST(nps AS DOUBLE) nps
            FROM {FQ}.gold_agent_performance"""
    )
    lowest = sql.run_query(
        f"""SELECT agent_name, team,
                   CAST(avg_handle_time_min AS DOUBLE) avg_handle_time_min,
                   CAST(nps AS DOUBLE) nps,
                   CAST(offer_conversion_rate AS DOUBLE) offer_conversion_rate,
                   CAST(save_rate AS DOUBLE) save_rate
            FROM {FQ}.gold_agent_performance
            ORDER BY save_rate ASC LIMIT 20"""
    )

    tier_order = {"Top Performer": 0, "On Target": 1, "Needs Coaching": 2, "At Risk": 3}
    tier_cards = sorted(
        [
            {
                "tier": t["tier"],
                "agents": int(sql.num(t["agents"])),
                "avg_save_rate": sql.num(t["avg_save_rate"]),
                "avg_handle_time": sql.num(t["avg_handle_time"]),
                "avg_nps": sql.num(t["avg_nps"]),
            }
            for t in tiers
        ],
        key=lambda x: tier_order.get(x["tier"], 9),
    )
    return {
        "tiers": tier_cards,
        "scatter": [
            {
                "agent_name": s["agent_name"],
                "team": s["team"],
                "tier": s["tier"],
                "save_rate": sql.num(s["save_rate"]),
                "handle_time": sql.num(s["avg_handle_time_min"]),
                "nps": sql.num(s["nps"]),
            }
            for s in scatter
        ],
        "coaching_table": [
            {
                "agent_name": r["agent_name"],
                "team": r["team"],
                "avg_handle_time_min": sql.num(r["avg_handle_time_min"]),
                "nps": sql.num(r["nps"]),
                "offer_conversion_rate": sql.num(r["offer_conversion_rate"]),
                "save_rate": sql.num(r["save_rate"]),
            }
            for r in lowest
        ],
        "insight": (
            "Agents who lead with speed-reliability data hit 68% save vs 35% for "
            "price-matching alone."
        ),
    }


# =============================================================== CHAT (MAS) ===
class ChatStart(BaseModel):
    message: str
    conversation_id: str | None = None
    history: list[dict] = []


@app.post("/api/chat")
async def chat_start(req: ChatStart):
    messages = [{"role": m["role"], "content": m["content"]} for m in req.history]
    messages.append({"role": "user", "content": req.message})
    job_id = mas.start_job(messages)
    return {"job_id": job_id}


@app.get("/api/chat/{job_id}")
async def chat_status(job_id: str):
    job = mas.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "status": job["status"],
        "response": job.get("response"),
        "error": job.get("error"),
        "elapsed": job.get("elapsed", 0.0),
    }


# ==================================================== CONVERSATIONS (CRUD) ===
class ConvCreate(BaseModel):
    title: str = "New conversation"


class ConvRename(BaseModel):
    title: str


class MsgSave(BaseModel):
    role: str
    content: str


def _safe(coro_result_default):
    """Decorator-ish helper unused; kept explicit try/except in handlers below."""
    return coro_result_default


@app.get("/api/conversations")
async def conversations_list(request: Request):
    email, token = get_identity(request)
    if not db.lakebase_configured() or not token:
        return {"conversations": [], "persistence": False}
    try:
        convs = await db.list_conversations(email, token)
        return {"conversations": convs, "persistence": True}
    except Exception as e:  # noqa: BLE001
        return {"conversations": [], "persistence": False, "error": str(e)}


@app.post("/api/conversations")
async def conversations_create(request: Request, body: ConvCreate):
    email, token = get_identity(request)
    if not db.lakebase_configured() or not token:
        raise HTTPException(status_code=503, detail="persistence unavailable")
    conv = await db.create_conversation(email, token, body.title)
    return conv


@app.get("/api/conversations/{conv_id}/messages")
async def conversation_messages(request: Request, conv_id: str):
    email, token = get_identity(request)
    if not db.lakebase_configured() or not token:
        return {"messages": []}
    try:
        return {"messages": await db.get_messages(email, token, conv_id)}
    except Exception:  # noqa: BLE001
        return {"messages": []}


@app.post("/api/conversations/{conv_id}/messages")
async def conversation_add_message(request: Request, conv_id: str, body: MsgSave):
    email, token = get_identity(request)
    if not db.lakebase_configured() or not token:
        return {"saved": False}
    try:
        await db.add_message(email, token, conv_id, body.role, body.content)
        return {"saved": True}
    except Exception as e:  # noqa: BLE001
        return {"saved": False, "error": str(e)}


@app.patch("/api/conversations/{conv_id}")
async def conversation_rename(request: Request, conv_id: str, body: ConvRename):
    email, token = get_identity(request)
    if not db.lakebase_configured() or not token:
        raise HTTPException(status_code=503, detail="persistence unavailable")
    await db.rename_conversation(email, token, conv_id, body.title)
    return {"renamed": True}


@app.delete("/api/conversations/{conv_id}")
async def conversation_delete(request: Request, conv_id: str):
    email, token = get_identity(request)
    if not db.lakebase_configured() or not token:
        raise HTTPException(status_code=503, detail="persistence unavailable")
    await db.delete_conversation(email, token, conv_id)
    return {"deleted": True}


@app.get("/api/health")
async def health():
    return {"status": "ok", "lakebase": db.lakebase_configured()}


# ============================================================ STATIC / SPA ===
_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "not found"}, status_code=404)
        candidate = os.path.join(_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_DIST, "index.html"))
