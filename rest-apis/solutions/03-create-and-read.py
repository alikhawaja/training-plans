"""Reference solution: create/read, reject a duplicate write, and verify state."""

import argparse
import json
import uuid

import httpx


def expect(response, status):
    if response.status_code != status:
        raise RuntimeError(
            f"Expected HTTP {status}, got {response.status_code}: {response.text}"
        )
    return response


def run(client, reference):
    body = {"reference": reference, "item": "Exercise notebook", "quantity": 3}
    created = expect(client.post("/api/v1/orders", json=body), 201)
    record = created.json()
    location = created.headers["Location"]
    if location != f'/api/v1/orders/{record["id"]}':
        raise RuntimeError("Location does not identify the created order")
    if any(record[field] != value for field, value in body.items()):
        raise RuntimeError("Created fields differ from the submitted order")
    read = expect(client.get(location), 200)
    if read.json() != record:
        raise RuntimeError("Read representation differs from the created order")

    duplicate = expect(client.post("/api/v1/orders", json=body), 409)
    if duplicate.headers["Content-Type"] != "application/problem+json":
        raise RuntimeError("Rejected request did not return Problem Details")
    problem = duplicate.json()
    if problem["status"] != duplicate.status_code or not problem["detail"]:
        raise RuntimeError("Error body does not explain the HTTP outcome")
    final = expect(client.get(location), 200)
    if final.json() != record:
        raise RuntimeError("Rejected request changed the original order")
    return {
        "id": record["id"],
        "reference": reference,
        "location": location,
        "create_status": created.status_code,
        "read_status": read.status_code,
        "duplicate_status": duplicate.status_code,
        "unchanged_after_rejection": True,
    }


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
