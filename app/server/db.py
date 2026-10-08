"""Lakebase (Postgres) chat persistence.

Connections authenticate as the *end user* using the OAuth token forwarded by
the Databricks Apps proxy (x-forwarded-access-token). We never call
generate_database_credential for the service principal. Every row is scoped by
user_email so each viewer only sees their own conversations.
"""
import os
import uuid
import contextlib

import asyncpg

PGHOST = os.environ.get("PGHOST")
PGPORT = int(os.environ.get("PGPORT", "5432"))
PGDATABASE = os.environ.get("PGDATABASE", "spectrum")
PGSSLMODE = os.environ.get("PGSSLMODE", "require")


def lakebase_configured() -> bool:
    return bool(PGHOST)


@contextlib.asynccontextmanager
async def user_conn(user_email: str, user_token: str):
    """Open a short-lived connection as the given user."""
    conn = await asyncpg.connect(
        host=PGHOST,
        port=PGPORT,
        database=PGDATABASE,
        user=user_email,
        password=user_token,
        ssl=PGSSLMODE,
        timeout=15,
    )
    try:
        yield conn
    finally:
        await conn.close()


async def list_conversations(user_email: str, token: str) -> list[dict]:
    async with user_conn(user_email, token) as c:
        rows = await c.fetch(
            """SELECT id, title, created_at, updated_at
               FROM conversations WHERE user_email = $1
               ORDER BY updated_at DESC""",
            user_email,
        )
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    ]


async def create_conversation(user_email: str, token: str, title: str) -> dict:
    conv_id = uuid.uuid4().hex
    async with user_conn(user_email, token) as c:
        await c.execute(
            """INSERT INTO conversations (id, user_email, title)
               VALUES ($1, $2, $3)""",
            conv_id, user_email, title[:120],
        )
    return {"id": conv_id, "title": title[:120]}


async def get_messages(user_email: str, token: str, conv_id: str) -> list[dict]:
    async with user_conn(user_email, token) as c:
        rows = await c.fetch(
            """SELECT role, content, created_at FROM messages
               WHERE conversation_id = $1 AND user_email = $2
               ORDER BY id ASC""",
            conv_id, user_email,
        )
    return [{"role": r["role"], "content": r["content"]} for r in rows]


async def add_message(user_email: str, token: str, conv_id: str, role: str, content: str):
    async with user_conn(user_email, token) as c:
        await c.execute(
            """INSERT INTO messages (conversation_id, user_email, role, content)
               VALUES ($1, $2, $3, $4)""",
            conv_id, user_email, role, content,
        )
        await c.execute(
            "UPDATE conversations SET updated_at = NOW() WHERE id = $1 AND user_email = $2",
            conv_id, user_email,
        )


async def rename_conversation(user_email: str, token: str, conv_id: str, title: str):
    async with user_conn(user_email, token) as c:
        await c.execute(
            "UPDATE conversations SET title = $1, updated_at = NOW() WHERE id = $2 AND user_email = $3",
            title[:120], conv_id, user_email,
        )


async def delete_conversation(user_email: str, token: str, conv_id: str):
    async with user_conn(user_email, token) as c:
        await c.execute(
            "DELETE FROM messages WHERE conversation_id = $1 AND user_email = $2",
            conv_id, user_email,
        )
        await c.execute(
            "DELETE FROM conversations WHERE id = $1 AND user_email = $2",
            conv_id, user_email,
        )
