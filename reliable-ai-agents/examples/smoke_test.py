"""Opt-in real-system checks. Requires seeded SQL, Zammad and the local listener."""

import json
import unittest

import httpx
import pymssql

from database import connection, order_evidence
from settings import STATE, local_url
from tickets import draft_note, get_ticket, inspect_action


class RealSystemTests(unittest.TestCase):
    def test_http_listener(self):
        response = httpx.get(local_url("APP_URL", "http://127.0.0.1:8010") + "/health", timeout=5, trust_env=False)
        response.raise_for_status()
        self.assertEqual(response.json()["status"], "healthy")

    def test_reader_view_and_database_enforced_denials(self):
        self.assertEqual(order_evidence("ORD-1001")["order"]["payment_status"], "captured")
        self.assertIsNone(order_evidence("ORD-9999")["order"])
        with connection() as conn:
            with conn.cursor() as cursor:
                for sql in [
                    "UPDATE dbo.orders SET shipment_status='shipped' WHERE 1=0",
                    "SELECT TOP 1 * FROM dbo.orders",
                    "CREATE TABLE dbo.forbidden (id int)",
                ]:
                    with self.assertRaises(pymssql.DatabaseError):
                        cursor.execute(sql)

    def test_real_zammad_read_and_local_draft_only(self):
        ids = json.loads((STATE / "tickets.json").read_text())
        ticket = get_ticket(ids[0])
        self.assertIn("ORD-1001", ticket["title"])
        action = draft_note(ids[0], "SMOKE: synthetic evidence collection; no approval granted.")
        self.assertEqual(inspect_action(action["id"])["status"], "pending")
        after = get_ticket(ids[0])
        self.assertFalse(any("SMOKE:" in a["body"] for a in after["articles"]))


if __name__ == "__main__":
    unittest.main()
