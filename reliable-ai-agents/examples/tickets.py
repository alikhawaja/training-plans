"""Restricted Zammad access; writes are operator-controlled, never agent tools."""

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager

import httpx

from settings import STATE, local_url, required


class AmbiguousWrite(RuntimeError):
    """A submitted action must be reconciled, not automatically retried."""


def client() -> httpx.Client:
    return httpx.Client(
        base_url=local_url("ZAMMAD_URL", "http://127.0.0.1:8081"),
        headers={
            "Authorization": f"Token token={required('ZAMMAD_TOKEN')}",
            "X-Zammad-Suppress-Notifications": "true",
        },
        timeout=10,
        follow_redirects=False,
        trust_env=False,
    )


def allowed_ticket(ticket_id: int) -> None:
    path = STATE / "tickets.json"
    ids = json.loads(path.read_text()) if path.exists() else []
    if ticket_id not in ids:
        raise ValueError("Ticket is not in this workshop's explicitly seeded allowlist")


def get_ticket(ticket_id: int) -> dict:
    allowed_ticket(ticket_id)
    with client() as api:
        ticket = api.get(f"/api/v1/tickets/{ticket_id}")
        ticket.raise_for_status()
        articles = api.get(f"/api/v1/ticket_articles/by_ticket/{ticket_id}")
        articles.raise_for_status()
    value = ticket.json()
    return {
        "source": f"zammad:ticket:{ticket_id}",
        "id": value["id"],
        "title": value["title"],
        "state_id": value["state_id"],
        "articles": [
            {"id": a["id"], "body": a["body"][:4000], "internal": a["internal"]}
            for a in articles.json()[-10:]
        ],
    }


@contextmanager
def ledger():
    STATE.mkdir(exist_ok=True)
    db = sqlite3.connect(STATE / "actions.sqlite", timeout=5)
    db.row_factory = sqlite3.Row
    db.execute(
        "CREATE TABLE IF NOT EXISTS actions ("
        "id TEXT PRIMARY KEY, digest TEXT UNIQUE NOT NULL, ticket_id INTEGER NOT NULL,"
        "body TEXT NOT NULL, status TEXT NOT NULL, article_id INTEGER)"
    )
    try:
        with db:
            yield db
    finally:
        db.close()


def draft_note(ticket_id: int, body: str) -> dict:
    allowed_ticket(ticket_id)
    if not 1 <= len(body.strip()) <= 3000:
        raise ValueError("Note must contain 1-3000 characters")
    digest = hashlib.sha256(f"{ticket_id}\n{body}".encode()).hexdigest()
    with ledger() as db:
        old = db.execute("SELECT id,status FROM actions WHERE digest=?", (digest,)).fetchone()
        if old:
            return dict(old)
        action_id = uuid.uuid4().hex
        db.execute(
            "INSERT INTO actions VALUES (?,?,?,?,?,NULL)",
            (action_id, digest, ticket_id, body, "pending"),
        )
    return {"id": action_id, "status": "pending", "message": "Operator must review exact content"}


def inspect_action(action_id: str) -> dict:
    with ledger() as db:
        row = db.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown action")
    return dict(row)


def decide(action_id: str, approve: bool) -> dict:
    action = inspect_action(action_id)
    if action["status"] != "pending":
        raise ValueError(f"Action is {action['status']}; inspect or reconcile instead of resubmitting")
    allowed_ticket(action["ticket_id"])
    with ledger() as db:
        changed = db.execute(
            "UPDATE actions SET status=? WHERE id=? AND status='pending'",
            ("submitting" if approve else "rejected", action_id),
        ).rowcount
        if changed != 1:
            raise ValueError("Another process changed this action")
    if not approve:
        return inspect_action(action_id)
    # Persist submitting BEFORE HTTP so crashes cannot cause an automatic duplicate.
    payload = {
        "ticket_id": action["ticket_id"],
        "subject": f"Workshop investigation [{action_id}]",
        "body": action["body"],
        "type": "note",
        "sender": "Agent",
        "internal": True,
        "content_type": "text/plain",
    }
    try:
        with client() as api:
            response = api.post("/api/v1/ticket_articles", json=payload)
            response.raise_for_status()
    except (httpx.TransportError, httpx.HTTPStatusError) as exc:
        with ledger() as db:
            db.execute("UPDATE actions SET status='unknown' WHERE id=?", (action_id,))
        raise AmbiguousWrite(f"Action {action_id} is unknown; reconcile before any retry") from exc
    # A successful HTTP response still requires read-back verification.
    return reconcile(action_id)


def reconcile(action_id: str) -> dict:
    action = inspect_action(action_id)
    if action["status"] not in {"submitting", "unknown", "done"}:
        raise ValueError("Only submitted/unknown/done actions can be reconciled")
    ticket = get_ticket(action["ticket_id"])
    # Fetch all articles: get_ticket intentionally limits agent-visible context.
    with client() as api:
        response = api.get(f"/api/v1/ticket_articles/by_ticket/{ticket['id']}")
        response.raise_for_status()
    matches = [
        a for a in response.json()
        if a.get("subject") == f"Workshop investigation [{action_id}]"
        and a["body"] == action["body"] and a["internal"] is True
    ]
    if len(matches) != 1:
        raise AmbiguousWrite(f"Found {len(matches)} matching articles; retain action and investigate manually")
    with ledger() as db:
        db.execute(
            "UPDATE actions SET status='done',article_id=? WHERE id=?",
            (matches[0]["id"], action_id),
        )
    return inspect_action(action_id)
