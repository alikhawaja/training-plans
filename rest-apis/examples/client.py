"""Inspect HTTP responses from the local training API; non-2xx errors exit nonzero."""

import argparse
import json
import os
import sys
import time
import uuid

import httpx


class ApiClient:
    def __init__(self, base_url="http://127.0.0.1:8000", token="workshop-demo-token", transport=None):
        self.http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=httpx.Timeout(5.0, connect=2.0),
            transport=transport,
        )

    def close(self):
        self.http.close()

    def request(self, method, path, *, headers=None, payload=None):
        method = method.upper()
        safe_to_retry = method in {"GET", "HEAD", "OPTIONS"}
        for attempt in range(3):
            try:
                response = self.http.request(method, path, headers=headers, json=payload)
            except httpx.TransportError as error:
                if not safe_to_retry or attempt == 2:
                    raise
                print(f"RETRY read after transport failure: {error}", file=sys.stderr)
            else:
                if not safe_to_retry or response.status_code not in {429, 502, 503, 504} or attempt == 2:
                    return response
                retry_after = response.headers.get("Retry-After")
                if retry_after is not None and (
                    not retry_after.isascii() or not retry_after.isdigit() or int(retry_after) > 5
                ):
                    # Do not retry earlier than a server's long or date-based deadline.
                    return response
                print(f"RETRY read after HTTP {response.status_code}", file=sys.stderr)
                delay = int(retry_after) if retry_after is not None else 0.25 * (2**attempt)
                time.sleep(delay)
                continue
            time.sleep(0.25 * (2**attempt))
        raise AssertionError("unreachable")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default=os.environ.get("TRAINING_API_TOKEN", "workshop-demo-token"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("health")
    create = commands.add_parser("create")
    create.add_argument("--reference", default=None)
    create.add_argument("--item", default="Training notebook")
    create.add_argument("--quantity", type=int, default=1)
    listing = commands.add_parser("list")
    listing.add_argument("--limit", type=int, default=10)
    listing.add_argument("--offset", type=int, default=0)
    listing.add_argument("--status")
    get = commands.add_parser("get")
    get.add_argument("id")
    get.add_argument("--if-none-match")
    for name in ("replace", "patch", "delete"):
        command = commands.add_parser(name)
        command.add_argument("id")
        command.add_argument("--etag", required=True)
        if name != "delete":
            command.add_argument("--item", required=name == "replace")
            command.add_argument("--quantity", type=int, required=name == "replace")
            command.add_argument("--status", required=name == "replace")
    args = parser.parse_args()
    path = "/api/v1/orders"
    method, payload, headers = "GET", None, {}
    if args.command == "health":
        path = "/health"
    elif args.command == "create":
        method = "POST"
        payload = {"reference": args.reference or f"lab-{uuid.uuid4().hex[:12]}",
                   "item": args.item, "quantity": args.quantity}
    elif args.command == "list":
        parameters = {"limit": args.limit, "offset": args.offset}
        if args.status is not None:
            parameters["status"] = args.status
        path += "?" + str(httpx.QueryParams(parameters))
    else:
        path += f"/{uuid.UUID(args.id)}"
        if args.command == "get":
            if args.if_none_match is not None:
                headers["If-None-Match"] = args.if_none_match
        else:
            method = {"replace": "PUT", "patch": "PATCH", "delete": "DELETE"}[args.command]
            headers["If-Match"] = args.etag
            if method != "DELETE":
                payload = {
                    field: getattr(args, field)
                    for field in ("item", "quantity", "status")
                    if getattr(args, field) is not None
                }
    client = ApiClient(args.base_url, args.token)
    try:
        response = client.request(method, path, headers=headers, payload=payload)
        print(f"HTTP {response.status_code}")
        for name in ("content-type", "location", "etag", "cache-control", "x-request-id", "retry-after"):
            if name in response.headers:
                print(f"{name}: {response.headers[name]}")
        if response.content:
            print(json.dumps(response.json(), indent=2))
        return 0 if response.is_success or response.status_code == 304 else 1
    finally:
        client.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (httpx.TransportError, ValueError) as error:
        print(f"Client failed: {error}", file=sys.stderr)
        sys.exit(1)
