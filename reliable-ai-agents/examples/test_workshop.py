import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

import optional
import service
import tickets
from tools import BudgetExceeded, RunControl


class LocalFaultTests(unittest.TestCase):
    def test_real_endpoint_fault_and_recovery(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(service, "STATE", Path(folder)):
            api = TestClient(service.app)
            self.assertEqual(api.get("/health").status_code, 200)
            (Path(folder) / "scenario.json").write_text('{"scenario":"unavailable"}')
            self.assertEqual(api.get("/health").status_code, 503)
            (Path(folder) / "scenario.json").write_text('{"scenario":"healthy"}')
            self.assertEqual(api.get("/health").status_code, 200)
            self.assertEqual(api.get("/logs", params={"order_id": "../secret"}).status_code, 422)

    def test_call_budget_prevents_further_operation(self):
        calls = []
        control = RunControl(max_calls=2, max_repeats=5)
        operation = lambda: calls.append(1) or {"status": "unavailable"}
        control.call("health", {}, operation)
        control.call("health", {}, operation)
        with self.assertRaises(BudgetExceeded):
            control.call("health", {}, operation)
        self.assertEqual(len(calls), 2)

    def test_unchanged_evidence_stops_but_changed_evidence_is_new(self):
        control = RunControl()
        for _ in range(2):
            control.call("health", {}, lambda: {"status": "unavailable"})
        control.call("health", {}, lambda: {"status": "healthy"})
        with self.assertRaises(BudgetExceeded):
            control.call("health", {}, lambda: {"status": "unavailable"})


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        (self.state / "tickets.json").write_text("[42]")
        self.patcher = patch.object(tickets, "STATE", self.state)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_rejection_and_duplicate_draft_never_post(self):
        with patch.object(tickets, "client") as api:
            action = tickets.draft_note(42, "Payment captured; shipment unknown. sql:ORD-1001")
            self.assertEqual(tickets.draft_note(42, "Payment captured; shipment unknown. sql:ORD-1001")["id"], action["id"])
            self.assertEqual(tickets.decide(action["id"], False)["status"], "rejected")
            api.assert_not_called()
        with self.assertRaises(ValueError):
            tickets.decide(action["id"], True)
        with self.assertRaises(ValueError):
            tickets.draft_note(99, "Wrong ticket")

    def test_timeout_marks_unknown_and_reconcile_does_not_repeat_post(self):
        action = tickets.draft_note(42, "An evidence-backed internal note.")
        stored = []
        posts = []

        def handler(request):
            if request.method == "POST":
                posts.append(request)
                stored.append({**json.loads(request.content), "id": 77})
                raise httpx.ReadTimeout("Lost response after server committed", request=request)
            if request.url.path.endswith("/tickets/42"):
                return httpx.Response(200, json={"id": 42, "title": "Synthetic", "state_id": 1})
            return httpx.Response(200, json=stored)

        def api():
            return httpx.Client(base_url="http://127.0.0.1", transport=httpx.MockTransport(handler))

        with patch.object(tickets, "client", api):
            with self.assertRaises(tickets.AmbiguousWrite):
                tickets.decide(action["id"], True)
            self.assertEqual(tickets.inspect_action(action["id"])["status"], "unknown")
            with self.assertRaises(ValueError):
                tickets.decide(action["id"], True)
            self.assertEqual(tickets.reconcile(action["id"])["status"], "done")
        self.assertEqual(len(posts), 1)

    def test_successful_post_must_pass_readback(self):
        action = tickets.draft_note(42, "Draft")
        def handler(request):
            if request.method == "POST":
                return httpx.Response(201, json={"id": 5})
            if request.url.path.endswith("/tickets/42"):
                return httpx.Response(200, json={"id": 42, "title": "Synthetic", "state_id": 1})
            return httpx.Response(200, json=[])
        with patch.object(tickets, "client", lambda: httpx.Client(
            base_url="http://127.0.0.1", transport=httpx.MockTransport(handler),
        )):
            with self.assertRaises(tickets.AmbiguousWrite):
                tickets.decide(action["id"], True)
        self.assertEqual(tickets.inspect_action(action["id"])["status"], "submitting")


class OptionalTests(unittest.TestCase):
    def test_retrieval_ingests_sources_and_rejects_empty_query(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(404 if len(requests) == 1 else 200, json={"result": {}})
        original_client = httpx.Client
        with patch.object(optional.httpx, "Client", lambda **kwargs: original_client(
            **kwargs, transport=httpx.MockTransport(handler),
        )):
            optional.ingest()
        points = json.loads(requests[-1].content)["points"]
        self.assertEqual(len(points), 3)
        self.assertTrue(all(p["payload"]["id"].startswith("RB-") for p in points))
        with self.assertRaises(ValueError):
            optional.search("")

    def test_email_draft_does_not_connect(self):
        with patch.object(optional.smtplib, "SMTP") as smtp:
            self.assertEqual(optional.email("Synthetic update", False)["status"], "draft")
            smtp.assert_not_called()


if __name__ == "__main__":
    unittest.main()
