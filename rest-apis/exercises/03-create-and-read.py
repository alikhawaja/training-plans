"""Learner exercise: implement a verified create/read interaction."""

import argparse
import json
import uuid

import httpx


def run(client, reference):
    """Return verified statuses and resource identifiers; raise on a failed check."""
    raise NotImplementedError(
        "Implement the independent exercise in modules/03-create-and-read/README.md"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default="workshop-demo-token")
    parser.add_argument("--reference", default=f"exercise-{uuid.uuid4().hex[:16]}")
    args = parser.parse_args()
    with httpx.Client(
        base_url=args.base_url,
        headers={"Authorization": f"Bearer {args.token}"},
        timeout=5.0,
    ) as client:
        result = run(client, args.reference)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
