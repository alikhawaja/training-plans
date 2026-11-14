import runpy
import unittest
from pathlib import Path

import httpx

run = runpy.run_path(Path(__file__).with_name("03-create-and-read.py"))["run"]


class ExerciseChecks(unittest.TestCase):
    def setUp(self):
        self.record = {
            "id": "14b45d75-a627-41d9-a847-9e88af55b089",
            "reference": "exercise-test",
            "item": "Exercise notebook",
            "quantity": 3,
            "status": "pending",
            "created_at": "2026-01-01T00:00:00+00:00",
            "version": 1,
        }
        self.location = f'/api/v1/orders/{self.record["id"]}'
        self.responses = [
            httpx.Response(201, json=self.record, headers={"Location": self.location}),
            httpx.Response(200, json=self.record),
            httpx.Response(
                409, json={"status": 409, "detail": "reference already exists"},
                headers={"Content-Type": "application/problem+json"},
            ),
            httpx.Response(200, json=self.record),
        ]
        self.requests = []

    def client(self):
        def handle(request):
            self.requests.append((request.method, request.url.path))
            return self.responses.pop(0)

        client = httpx.Client(base_url="http://workshop", transport=httpx.MockTransport(handle))
        self.addCleanup(client.close)
        return client

    def test_reference_follows_location_and_checks_final_state(self):
        result = run(self.client(), self.record["reference"])
        self.assertEqual(self.requests, [
            ("POST", "/api/v1/orders"), ("GET", self.location),
            ("POST", "/api/v1/orders"), ("GET", self.location),
        ])
        self.assertEqual(result["duplicate_status"], 409)
        self.assertTrue(result["unchanged_after_rejection"])

    def test_unexpected_create_status_stops_without_reading_or_retrying(self):
        self.responses[0] = httpx.Response(401, json={"detail": "bad token"})
        with self.assertRaisesRegex(RuntimeError, "Expected HTTP 201, got 401"):
            run(self.client(), self.record["reference"])
        self.assertEqual(self.requests, [("POST", "/api/v1/orders")])

    def test_changed_final_record_is_not_reported_as_success(self):
        self.responses[-1] = httpx.Response(200, json={**self.record, "quantity": 4})
        with self.assertRaisesRegex(RuntimeError, "changed the original order"):
            run(self.client(), self.record["reference"])


if __name__ == "__main__":
    unittest.main()
