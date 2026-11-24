"""Use Requests directly to create, read, update, and delete one demo order."""

import argparse
import json
import os
import sys
import uuid

import requests

TIMEOUT = (2, 5)


def inspect_response(response, expected):
    print(f"{response.request.method} {response.url}: HTTP {response.status_code}")
    for name in ("Location", "ETag", "X-Request-ID"):
        if name in response.headers:
            print(f"{name}: {response.headers[name]}")
    if response.content:
        print(json.dumps(response.json(), indent=2))
    response.raise_for_status()
    if response.status_code != expected:
        raise ValueError(f"Expected HTTP {expected}, got {response.status_code}")


def run_demo(base_url="http://127.0.0.1:8000", token="workshop-demo-token"):
    orders_url = base_url.rstrip("/") + "/api/v1/orders"
    with requests.Session() as session:
        session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })
        created = session.post(
            orders_url,
            json={"reference": f"req-{uuid.uuid4().hex}", "item": "Requests notebook",
                  "quantity": 2},
            timeout=TIMEOUT, allow_redirects=False,
        )
        inspect_response(created, 201)
        order_url = f"{orders_url}/{uuid.UUID(created.json()['id'])}"
        try:
            page = session.get(orders_url, params={"limit": 2}, timeout=TIMEOUT,
                               allow_redirects=False)
            inspect_response(page, 200)

            read = session.get(order_url, timeout=TIMEOUT, allow_redirects=False)
            inspect_response(read, 200)
            unchanged = session.get(
                order_url, headers={"If-None-Match": read.headers["ETag"]},
                timeout=TIMEOUT, allow_redirects=False,
            )
            inspect_response(unchanged, 304)

            patched = session.patch(
                order_url, headers={"If-Match": read.headers["ETag"]},
                json={"quantity": 3}, timeout=TIMEOUT, allow_redirects=False,
            )
            inspect_response(patched, 200)
            replaced = session.put(
                order_url, headers={"If-Match": patched.headers["ETag"]},
                json={"item": "Requests notebook", "quantity": 4, "status": "confirmed"},
                timeout=TIMEOUT, allow_redirects=False,
            )
            inspect_response(replaced, 200)
        finally:
            # Re-read the current version before deleting only this demo's order.
            current = session.get(order_url, timeout=TIMEOUT, allow_redirects=False)
            inspect_response(current, 200)
            deleted = session.delete(
                order_url, headers={"If-Match": current.headers["ETag"]},
                timeout=TIMEOUT, allow_redirects=False,
            )
            inspect_response(deleted, 204)
        print("PASS: Requests CRUD demo completed; its order was deleted.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default=os.environ.get("TRAINING_API_TOKEN", "workshop-demo-token"))
    args = parser.parse_args()
    run_demo(args.base_url, args.token)


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, ValueError, KeyError) as error:
        print(f"Requests demo failed: {error}", file=sys.stderr)
        sys.exit(1)
