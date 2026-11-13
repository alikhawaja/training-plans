"""Operator commands. These functions are NOT exposed to the agent."""

import argparse
import json
import os
import secrets

from database import order_evidence, seed_sql
from settings import ROOT, STATE
from tickets import client, decide, get_ticket, inspect_action, reconcile


def configure() -> None:
    target = ROOT / ".env"
    if target.exists():
        raise ValueError(".env already exists; edit it rather than replacing credentials")
    text = (ROOT / ".env.example").read_text()
    for name in ("MSSQL_SA_PASSWORD", "SQL_READER_PASSWORD", "POSTGRES_PASSWORD"):
        text = text.replace(f"{name}=\n", f"{name}=Lab9!{secrets.token_urlsafe(24)}\n")
    target.write_text(text, encoding="utf-8")
    print("Created ignored .env with generated local passwords; API keys remain empty.")


def seed_tickets() -> None:
    STATE.mkdir(exist_ok=True)
    target = STATE / "tickets.json"
    if target.exists():
        for ticket_id in json.loads(target.read_text()):
            get_ticket(ticket_id)
        print(target.read_text())
        return
    with client() as api:
        me = api.get("/api/v1/users/me")
        me.raise_for_status()
        ids = []
        # Record each successful creation immediately. A partial seed must be
        # reconciled manually rather than rerun and silently creating duplicates.
        journal = STATE / "seed-started.json"
        if journal.exists():
            raise ValueError("A prior seed started. Inspect seed-started.json and Zammad before retrying.")
        journal.write_text("[]")
        for order_id in ("ORD-1001", "ORD-1002", "ORD-9999"):
            response = api.post("/api/v1/tickets", json={
                "title": f"[ReliableAgentsLab] Investigate {order_id}",
                "group": "LabSupport",
                "customer_id": me.json()["id"],
                "article": {
                    "subject": f"Investigation {order_id}",
                    "body": f"Synthetic customer reports payment completed but order {order_id} did not arrive.",
                    "type": "note", "sender": "Customer", "internal": False,
                    "content_type": "text/plain",
                },
            })
            response.raise_for_status()
            ids.append(response.json()["id"])
            journal.write_text(json.dumps(ids))
    target.write_text(json.dumps(ids))
    journal.unlink()
    print(f"Seeded ticket IDs: {ids}. Open Zammad to inspect the actual records.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("configure")
    sub.add_parser("seed-sql")
    sub.add_parser("seed-tickets")
    p = sub.add_parser("scenario")
    p.add_argument("value", choices=["healthy", "unavailable", "injection"])
    p = sub.add_parser("order")
    p.add_argument("order_id")
    p = sub.add_parser("ticket")
    p.add_argument("ticket_id", type=int)
    p = sub.add_parser("action")
    p.add_argument("action_id")
    p = sub.add_parser("decide")
    p.add_argument("action_id")
    p.add_argument("decision", choices=["approve", "reject"])
    p = sub.add_parser("reconcile")
    p.add_argument("action_id")
    args = parser.parse_args()
    if args.command == "configure":
        configure()
    elif args.command == "seed-sql":
        seed_sql()
        print("Seeded three synthetic orders and the restricted reader.")
    elif args.command == "seed-tickets":
        seed_tickets()
    elif args.command == "scenario":
        STATE.mkdir(exist_ok=True)
        (STATE / "scenario.json").write_text(json.dumps({"scenario": args.value}))
        print(f"Scenario changed to {args.value}; no real order or payment was modified.")
    elif args.command == "order":
        print(json.dumps(order_evidence(args.order_id), indent=2))
    elif args.command == "ticket":
        print(json.dumps(get_ticket(args.ticket_id), indent=2))
    elif args.command == "action":
        print(json.dumps(inspect_action(args.action_id), indent=2))
    elif args.command == "decide":
        print(json.dumps(inspect_action(args.action_id), indent=2))
        if args.decision == "approve":
            confirmation = input("Type the full action ID to approve EXACTLY this internal note: ")
            if confirmation != args.action_id:
                raise ValueError("Approval not confirmed; no action submitted")
        print(json.dumps(decide(args.action_id, args.decision == "approve"), indent=2))
    elif args.command == "reconcile":
        print(json.dumps(reconcile(args.action_id), indent=2))


if __name__ == "__main__":
    main()
