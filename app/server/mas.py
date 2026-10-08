"""Multi-Agent Supervisor (MAS) endpoint client with async job polling.

The Databricks Apps proxy buffers streaming responses, so instead of SSE we
run the (10-30s+) MAS call in a background task and let the frontend poll for
completion.
"""
import asyncio
import re
import time
import uuid

import aiohttp

from .config import get_workspace_host, get_sp_token, MAS_ENDPOINT

_NAME_TAG = re.compile(r"^\s*<name>.*</name>\s*$", re.DOTALL)

# In-memory job store: job_id -> {status, response, error, started, elapsed}
JOBS: dict[str, dict] = {}


def _extract_answer(payload: dict) -> str:
    """Pull the final human-readable assistant answer from a MAS responses payload."""
    output = payload.get("output") or []
    texts: list[str] = []
    for item in output:
        if item.get("type") != "message":
            continue
        parts = item.get("content") or []
        chunk = "".join(
            p.get("text", "") for p in parts if p.get("type") == "output_text"
        ).strip()
        if not chunk or _NAME_TAG.match(chunk):
            continue  # skip routing markers like <name>analyst</name>
        texts.append(chunk)
    if texts:
        return texts[-1]  # supervisor's final synthesized answer
    # Fallbacks for other response shapes
    if isinstance(payload.get("content"), str):
        return payload["content"]
    choices = payload.get("choices")
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return "I wasn't able to generate a response. Please try again."


async def _call_mas(messages: list[dict]) -> str:
    host = get_workspace_host()
    token = get_sp_token()
    url = f"{host}/serving-endpoints/{MAS_ENDPOINT}/invocations"
    body = {"input": messages}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=body, headers=headers) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"MAS endpoint error {resp.status}: {text[:500]}")
            import json
            return _extract_answer(json.loads(text))


async def _run_job(job_id: str, messages: list[dict]):
    job = JOBS[job_id]
    try:
        answer = await _call_mas(messages)
        job["status"] = "done"
        job["response"] = answer
    except Exception as e:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = str(e)
    finally:
        job["elapsed"] = round(time.time() - job["started"], 1)


def start_job(messages: list[dict]) -> str:
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "pending", "response": None, "error": None,
                    "started": time.time(), "elapsed": 0.0}
    asyncio.create_task(_run_job(job_id, messages))
    return job_id


def get_job(job_id: str) -> dict | None:
    job = JOBS.get(job_id)
    if job and job["status"] == "pending":
        job["elapsed"] = round(time.time() - job["started"], 1)
    return job
