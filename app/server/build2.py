"""Build 2 — the decision app (Visualize / Assist / Act), built layer by layer.

Reads the READ-ONLY Build 1 synced UC table (telcoabc_retention.synced_churn_risk_scores)
via the ops.v_retention_worklist view and persists ALL state/actions to writable Postgres
tables (ops.retention_actions, ops.workflow_events). Never writes the synced table.
"""
import os
import asyncpg
from fastapi import APIRouter

router = APIRouter(prefix="/build2", tags=["build2"])

PGHOST = os.environ.get("PGHOST")
PGDATABASE = os.environ.get("PGDATABASE", "spectrum")


async def _conn(user_email: str, token: str):
    return await asyncpg.connect(host=PGHOST, port=int(os.environ.get("PGPORT", "5432")),
                                 database=PGDATABASE, user=user_email, password=token,
                                 ssl=os.environ.get("PGSSLMODE", "require"), timeout=15)


# ---------------------------------------------------------------------------
# Layer 1 — VISUALIZE: ranked/flagged live worklist (the decision surface).
# ---------------------------------------------------------------------------
@router.get("/worklist")
async def worklist(user_email: str, token: str, limit: int = 10):
    """Top at-risk customers, ranked, flagged needs_action until a committed action
    closes the loop. Refreshed by a scheduled trigger (see log_trigger)."""
    c = await _conn(user_email, token)
    try:
        rows = await c.fetch(
            """SELECT customer_id, market, churn_score, risk_tier, case_id, competitor_id,
                      recommended_offer_id, status, needs_action, priority_rank
               FROM ops.v_retention_worklist ORDER BY priority_rank LIMIT $1""", limit)
        return [dict(r) for r in rows]
    finally:
        await c.close()


async def log_trigger(user_email: str, token: str, source: str = "schedule"):
    """Scheduled/system refresh writes a trigger event + flags — scores higher than a
    person opening the view. Wired to a Databricks job schedule in production."""
    c = await _conn(user_email, token)
    try:
        await c.execute(
            """INSERT INTO ops.workflow_events (event_type, trigger_source, entity_type, entity_id, actor, detail)
               SELECT 'view_refresh_trigger', $1, 'view', 'v_retention_worklist', 'system',
                      jsonb_build_object('flagged_needing_action', count(*) FILTER (WHERE needs_action))
               FROM ops.v_retention_worklist""", source)
    finally:
        await c.close()


# ---------------------------------------------------------------------------
# Layer 2 — ASSIST: explain a flag, run what-ifs, draft a memo. Retrieval comes
# from the Build 1 Lakebase Search index (ops.case_notes hybrid vector+FTS), NOT a
# separate vector store. LLM = databricks-claude-haiku-4-5; embeddings = gte-large-en.
# ---------------------------------------------------------------------------
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

LLM = "databricks-claude-haiku-4-5"
EMB = "databricks-gte-large-en"


async def _search_notes(c, query_text: str, k: int = 5):
    """Hybrid (vector + full-text) retrieval over the Build 1 Lakebase Search index."""
    w = WorkspaceClient()
    qv = "[" + ",".join(f"{x:.6f}" for x in w.serving_endpoints.query(name=EMB, input=[query_text]).data[0].embedding) + "]"
    return await c.fetch(f"""
      WITH q AS (SELECT '{qv}'::vector qv, to_tsquery('english','cancel | switch | pricing | outage') qt),
      vec AS (SELECT note_id, RANK() OVER (ORDER BY embedding <=> q.qv) r FROM ops.case_notes n, q ORDER BY embedding <=> q.qv LIMIT 15),
      ft  AS (SELECT note_id, RANK() OVER (ORDER BY ts_rank(note_tsv,q.qt) DESC) r FROM ops.case_notes n, q WHERE note_tsv @@ q.qt ORDER BY ts_rank(note_tsv,q.qt) DESC LIMIT 15)
      SELECT n.note_text FROM ops.case_notes n
      LEFT JOIN vec ON vec.note_id=n.note_id LEFT JOIN ft ON ft.note_id=n.note_id
      WHERE vec.note_id IS NOT NULL OR ft.note_id IS NOT NULL
      ORDER BY COALESCE(1.0/(60+vec.r),0)+COALESCE(1.0/(60+ft.r),0) DESC LIMIT {k}""")


def _llm(system: str, user: str, max_tokens: int = 700) -> str:
    w = WorkspaceClient()
    r = w.serving_endpoints.query(name=LLM, messages=[
        ChatMessage(role=ChatMessageRole.SYSTEM, content=system),
        ChatMessage(role=ChatMessageRole.USER, content=user)], max_tokens=max_tokens)
    return r.as_dict()["choices"][0]["message"]["content"]


@router.post("/assist/explain")
async def explain(user_email: str, token: str, customer_id: str, question: str):
    c = await _conn(user_email, token)
    try:
        notes = [r["note_text"] for r in await _search_notes(c, question)]
        ans = _llm("You are a retention analyst. Ground answers in the retrieved notes.",
                   f"{question}\n\nRetrieved notes:\n" + "\n".join(f"- {n}" for n in notes))
        await c.execute("""INSERT INTO ops.workflow_events (event_type, trigger_source, entity_type, entity_id, actor, detail)
                           VALUES ('explanation','user','customer',$1,'assistant',$2)""",
                        customer_id, '{"endpoint":"%s"}' % LLM)
        return {"answer": ans, "retrieved": notes}
    finally:
        await c.close()


# ---------------------------------------------------------------------------
# Layer 3 — ACT: propose an action, a human approves/corrects, then commit. The
# committed decision removes the flag on the next read of the worklist (closed loop).
# ---------------------------------------------------------------------------
@router.post("/actions/propose")
async def propose_action(user_email: str, token: str, case_id: int, customer_id: str,
                         offer_id: str, rationale: str):
    c = await _conn(user_email, token)
    try:
        aid = await c.fetchval(
            """INSERT INTO ops.retention_actions (case_id, customer_id, action_type, proposed_offer_id, proposed_by, rationale)
               VALUES ($1,$2,'present_offer',$3,'system',$4) RETURNING action_id""",
            case_id, customer_id, offer_id, rationale)
        await c.execute("""INSERT INTO ops.workflow_events (event_type,trigger_source,entity_type,entity_id,actor,detail)
                           VALUES ('action_proposed','system','action',$1,'system',$2)""",
                        str(aid), '{"proposed_offer_id":"%s"}' % offer_id)
        return {"action_id": aid, "status": "proposed"}
    finally:
        await c.close()


@router.post("/actions/{action_id}/approve")
async def approve_action(action_id: int, user_email: str, token: str,
                         final_offer_id: str, corrected: bool = False):
    """Human approves or corrects, THEN commits — the write only lands here."""
    c = await _conn(user_email, token)
    try:
        status = "corrected" if corrected else "approved"
        await c.execute("""UPDATE ops.retention_actions
                           SET approval_status=$1, approver=$2, final_offer_id=$3, committed_at=now()
                           WHERE action_id=$4""", status, user_email, final_offer_id, action_id)
        row = await c.fetchrow("SELECT case_id FROM ops.retention_actions WHERE action_id=$1", action_id)
        await c.execute("INSERT INTO ops.offers_presented (case_id, offer_id) VALUES ($1,$2)",
                        row["case_id"], final_offer_id)
        for et in ("action_approved", "action_committed"):
            await c.execute("""INSERT INTO ops.workflow_events (event_type,trigger_source,entity_type,entity_id,actor,detail)
                               VALUES ($1,'user','action',$2,$3,$4)""",
                            et, str(action_id), user_email, '{"final_offer_id":"%s"}' % final_offer_id)
        return {"action_id": action_id, "status": status, "committed": True}
    finally:
        await c.close()
