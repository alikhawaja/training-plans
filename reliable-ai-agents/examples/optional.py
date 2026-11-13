"""Optional local Qdrant retrieval and Mailpit delivery, without paid embeddings."""

import argparse
import hashlib
import json
import math
import re
import smtplib
from email.message import EmailMessage

import httpx

from settings import FIXTURES

COLLECTION = "reliable_agents_runbooks"


def embed(text: str) -> list[float]:
    """Signed lexical feature hashing, NOT a learned semantic embedding."""
    vector = [0.0] * 64
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        vector[digest[0] % 64] += 1 if digest[1] % 2 else -1
    norm = math.sqrt(sum(x * x for x in vector)) or 1
    return [x / norm for x in vector]


def ingest() -> dict:
    books = json.loads((FIXTURES / "runbooks.json").read_text())
    with httpx.Client(base_url="http://127.0.0.1:6333", timeout=10, trust_env=False) as api:
        exists = api.get(f"/collections/{COLLECTION}")
        if exists.status_code == 404:
            response = api.put(f"/collections/{COLLECTION}", json={
                "vectors": {"size": 64, "distance": "Cosine"},
            })
            response.raise_for_status()
        else:
            exists.raise_for_status()
        response = api.put(f"/collections/{COLLECTION}/points?wait=true", json={
            "points": [
                {"id": i, "vector": embed(book["title"] + " " + book["text"]), "payload": book}
                for i, book in enumerate(books, 1)
            ],
        })
        response.raise_for_status()
        return response.json()


def search(query: str) -> dict:
    if not 1 <= len(query) <= 500:
        raise ValueError("Query must contain 1-500 characters")
    with httpx.Client(timeout=10, trust_env=False) as api:
        response = api.post(
            f"http://127.0.0.1:6333/collections/{COLLECTION}/points/query",
            json={"query": embed(query), "limit": 2, "with_payload": True},
        )
        response.raise_for_status()
        return response.json()


def email(body: str, approve: bool) -> dict:
    if not 1 <= len(body.strip()) <= 3000:
        raise ValueError("Body must contain 1-3000 characters")
    message = EmailMessage()
    message["From"] = "support@example.invalid"
    message["To"] = "student@example.invalid"
    message["Subject"] = "Synthetic incident update"
    message.set_content(body)
    print(message)
    if not approve:
        return {"status": "draft", "message": "No SMTP request made"}
    if input("Type SEND-TO-LOCAL-MAILPIT to approve this exact message: ") != "SEND-TO-LOCAL-MAILPIT":
        raise ValueError("Approval not confirmed")
    # No automatic retry: SMTP disconnects can leave delivery status ambiguous.
    with smtplib.SMTP("127.0.0.1", 1025, timeout=5) as smtp:
        smtp.send_message(message)
    return {"status": "submitted", "verify": "Inspect http://127.0.0.1:8025"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest")
    p = sub.add_parser("search")
    p.add_argument("query")
    p = sub.add_parser("email")
    p.add_argument("body")
    p.add_argument("--approve", action="store_true")
    args = parser.parse_args()
    result = ingest() if args.command == "ingest" else search(args.query) if args.command == "search" else email(args.body, args.approve)
    print(json.dumps(result, indent=2))
