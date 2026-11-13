"""Verify the live API using isolated orders, then delete only those test orders."""

import argparse
import uuid

from client import ApiClient

ORDERS = "/api/v1/orders"


def expect(response, status):
    if response.status_code != status:
        raise RuntimeError(f"Expected HTTP {status}, got {response.status_code}: {response.text}")
    return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default="workshop-demo-token")
    args = parser.parse_args()
    client = ApiClient(args.base_url, args.token)
    paths = []
    try:
        expect(client.request("GET", "/health"), 200)
        unauthorized = expect(client.request("GET", ORDERS, headers={"Authorization": "Bearer wrong"}), 401)
        if unauthorized.json()["request_id"] != unauthorized.headers["X-Request-ID"]:
            raise RuntimeError("Problem response request ID does not match the header")
        for _ in range(2):
            reference = "smoke-" + uuid.uuid4().hex[:16]
            body = {"reference": reference, "item": "Smoke notebook", "quantity": 2}
            created = expect(client.request("POST", ORDERS, payload=body), 201)
            path = created.headers["Location"]
            paths.append(path)
            expect(client.request("POST", ORDERS, payload=body), 409)
            read = expect(client.request("GET", path), 200)
            etag = read.headers["ETag"]
            expect(client.request("GET", path, headers={"If-None-Match": etag}), 304)
            expect(client.request("PATCH", path, payload={"quantity": 3}), 428)
            patched = expect(client.request(
                "PATCH", path, headers={"If-Match": etag}, payload={"quantity": 3}
            ), 200)
            expect(client.request(
                "PATCH", path, headers={"If-Match": etag}, payload={"quantity": 4}
            ), 412)
            replaced = expect(client.request(
                "PUT", path, headers={"If-Match": patched.headers["ETag"]},
                payload={"item": "Updated notebook", "quantity": 4, "status": "confirmed"}
            ), 200)
            if replaced.json()["quantity"] != 4 or replaced.json()["reference"] != reference:
                raise RuntimeError("Update changed an unexpected field")
        invalid = {"reference": "invalid-" + uuid.uuid4().hex[:12], "item": "Book", "quantity": 0}
        expect(client.request("POST", ORDERS, payload=invalid), 422)
        page = expect(client.request("GET", ORDERS + "?limit=1&status=confirmed"), 200).json()
        if len(page["items"]) != 1 or page["total"] < 2 or page["next"] is None:
            raise RuntimeError(f"Unexpected page shape: {page}")
        second = expect(client.request("GET", page["next"]), 200).json()
        if page["items"][0]["id"] == second["items"][0]["id"]:
            raise RuntimeError("Two pages returned the same first item")
    finally:
        try:
            for path in paths:
                current = client.request("GET", path)
                if current.status_code == 404:
                    continue
                expect(current, 200)
                deleted = expect(client.request(
                    "DELETE", path, headers={"If-Match": current.headers["ETag"]}
                ), 204)
                if deleted.content:
                    raise RuntimeError("DELETE 204 returned a body")
                expect(client.request("GET", path), 404)
            print(f"CLEANUP: deleted {len(paths)} smoke-test orders.")
        finally:
            client.close()
    print("PASS: live CRUD, authentication, validation, conflict, paging, ETags, and preconditions.")


if __name__ == "__main__":
    main()
