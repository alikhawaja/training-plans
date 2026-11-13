import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from api import create_app
from client import ApiClient

TOKEN = {"Authorization": "Bearer workshop-demo-token"}
ORDERS = "/api/v1/orders"


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "orders.db"
        self.client = TestClient(create_app(self.path, token="workshop-demo-token"))
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def create(self, **changes):
        return self.client.post(
            ORDERS, headers=TOKEN,
            json={"reference": uuid.uuid4().hex, "item": "Notebook", "quantity": 2, **changes},
        )

    def test_create_read_update_and_delete_with_contract_headers(self):
        created = self.create()
        self.assertEqual(created.status_code, 201)
        location, first_etag = created.headers["Location"], created.headers["ETag"]
        read = self.client.get(location, headers=TOKEN)
        self.assertEqual(read.json(), created.json())
        unchanged = self.client.get(location, headers={**TOKEN, "If-None-Match": first_etag})
        self.assertEqual((unchanged.status_code, unchanged.content), (304, b""))
        patch_response = self.client.patch(
            location, headers={**TOKEN, "If-Match": first_etag}, json={"status": "confirmed"}
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertNotEqual(patch_response.headers["ETag"], first_etag)
        self.assertEqual(patch_response.json()["quantity"], 2)
        replaced = self.client.put(
            location, headers={**TOKEN, "If-Match": patch_response.headers["ETag"]},
            json={"item": "Pen", "quantity": 3, "status": "shipped"},
        )
        self.assertEqual(replaced.status_code, 200)
        deleted = self.client.delete(location, headers={**TOKEN, "If-Match": replaced.headers["ETag"]})
        self.assertEqual((deleted.status_code, deleted.content), (204, b""))
        self.assertEqual(self.client.get(location, headers=TOKEN).status_code, 404)

    def test_missing_auth_and_validation_are_explicit_problem_responses(self):
        unauthorized = self.client.get(ORDERS)
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.headers["WWW-Authenticate"], "Bearer")
        self.assertEqual(unauthorized.headers["Content-Type"], "application/problem+json")
        self.assertEqual(unauthorized.json()["request_id"], unauthorized.headers["X-Request-ID"])
        self.assertEqual(self.client.get(ORDERS, headers={"Authorization": "Bearer wrong"}).status_code, 401)
        for changes in ({"quantity": 0}, {"quantity": True}, {"item": "   "}, {"unknown": "x"}):
            with self.subTest(changes=changes):
                result = self.create(**changes)
                self.assertEqual(result.status_code, 422)
                self.assertIn("errors", result.json())
        self.assertEqual(self.client.get(ORDERS + "/not-a-uuid", headers=TOKEN).status_code, 422)

    def test_duplicate_reference_and_invalid_patch_do_not_change_state(self):
        created = self.create(reference="same-reference")
        self.assertEqual(self.create(reference="same-reference").status_code, 409)
        location = created.headers["Location"]
        for body in ({}, {"item": None}, {"quantity": -1}):
            self.assertEqual(
                self.client.patch(
                    location, headers={**TOKEN, "If-Match": created.headers["ETag"]}, json=body
                ).status_code, 422,
            )
        self.assertEqual(self.client.get(location, headers=TOKEN).json()["version"], 1)

    def test_concurrent_edit_preconditions_prevent_overwrite_and_delete(self):
        created = self.create()
        location = created.headers["Location"]
        self.assertEqual(self.client.patch(location, headers=TOKEN, json={"quantity": 3}).status_code, 428)
        new = self.client.patch(
            location, headers={**TOKEN, "If-Match": created.headers["ETag"]}, json={"quantity": 4}
        )
        self.assertEqual(new.status_code, 200)
        stale = {**TOKEN, "If-Match": created.headers["ETag"]}
        self.assertEqual(self.client.patch(location, headers=stale, json={"quantity": 5}).status_code, 412)
        self.assertEqual(self.client.delete(location, headers=stale).status_code, 412)
        self.assertEqual(self.client.get(location, headers=TOKEN).json()["quantity"], 4)

    def test_pagination_filters_and_persistence_across_app_restart(self):
        first = self.create()
        self.create()
        self.client.patch(
            first.headers["Location"], headers={**TOKEN, "If-Match": first.headers["ETag"]},
            json={"status": "shipped"},
        )
        page = self.client.get(ORDERS + "?limit=1", headers=TOKEN).json()
        self.assertEqual(page["total"], 2)
        self.assertEqual(len(page["items"]), 1)
        next_page = self.client.get(page["next"], headers=TOKEN).json()
        self.assertNotEqual(page["items"][0]["id"], next_page["items"][0]["id"])
        self.assertIsNone(next_page["next"])
        filtered = self.client.get(ORDERS + "?status=shipped", headers=TOKEN).json()
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(self.client.get(ORDERS + "?limit=51", headers=TOKEN).status_code, 422)
        with TestClient(create_app(self.path, token="workshop-demo-token")) as restarted:
            self.assertEqual(restarted.get(ORDERS, headers=TOKEN).json()["total"], 2)

    def test_openapi_describes_bearer_auth_and_actual_problem_media_type(self):
        specification = self.client.get("/openapi.json").json()
        operation = specification["paths"][ORDERS]["post"]
        self.assertIn({"HTTPBearer": []}, operation["security"])
        content = operation["responses"]["422"]["content"]
        self.assertIn("application/problem+json", content)
        self.assertNotIn("application/json", content)
        self.assertIn("request_id", content["application/problem+json"]["schema"]["required"])


class ClientTests(unittest.TestCase):
    def test_get_retry_is_bounded_and_honors_short_retry_after(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(503, headers={"Retry-After": "1"})

        client = ApiClient(transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        with patch("client.time.sleep") as sleep:
            response = client.request("GET", ORDERS)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleep.call_count, 2)
        sleep.assert_called_with(1)

    def test_post_transport_failure_is_not_retried(self):
        calls = []

        def handler(request):
            calls.append(request)
            raise httpx.ReadTimeout("response lost", request=request)

        client = ApiClient(transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        with self.assertRaises(httpx.ReadTimeout):
            client.request("POST", ORDERS, payload={"item": "Notebook"})
        self.assertEqual(len(calls), 1)

    def test_long_retry_after_and_validation_errors_are_not_retried(self):
        for status, headers in ((429, {"Retry-After": "60"}), (422, {})):
            calls = []

            def handler(request):
                calls.append(request)
                return httpx.Response(status, headers=headers)

            client = ApiClient(transport=httpx.MockTransport(handler))
            self.addCleanup(client.close)
            with patch("client.time.sleep") as sleep:
                self.assertEqual(client.request("GET", ORDERS).status_code, status)
                sleep.assert_not_called()
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
