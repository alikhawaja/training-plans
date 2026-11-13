import base64
import json
import sqlite3
import unittest
from contextlib import closing
from unittest.mock import Mock, patch

from common import InvalidEvent, ReliableProducer, decode_event, make_event
from consumer import dead_letter, open_store, process_event, process_with_retry
from consumer import main as consume


class EventTests(unittest.TestCase):
    def test_valid_event_and_contract_rejections(self):
        event = make_event("order-1")
        self.assertEqual(decode_event(json.dumps(event), b"order-1"), event)
        for value, key in [
            (None, b"order-1"),
            (b"\xff", b"order-1"),
            (b"[]", b"order-1"),
            (json.dumps(event), b"wrong-key"),
            (json.dumps({**event, "amount_cents": True}), b"order-1"),
            (json.dumps({**event, "schema_version": True}), b"order-1"),
            (json.dumps({**event, "occurred_at": "yesterday"}), b"order-1"),
            (json.dumps({**event, "status": "unknown"}), b"order-1"),
        ]:
            with self.subTest(value=value), self.assertRaises(InvalidEvent):
                decode_event(value, key)

    def test_replay_does_not_repeat_business_effect_and_conflicts_fail(self):
        with closing(open_store(":memory:")) as connection:
            event = make_event("order-1")
            self.assertTrue(process_event(connection, event))
            self.assertFalse(process_event(connection, event))
            with self.assertRaises(InvalidEvent):
                process_event(connection, {**event, "amount_cents": 1})
            self.assertEqual(
                connection.execute("SELECT event_count FROM order_totals").fetchone()[0], 1
            )

    def test_business_failure_rolls_back_deduplication_marker(self):
        with closing(open_store(":memory:")) as connection:
            connection.execute("DROP TABLE order_totals")
            with self.assertRaises(sqlite3.OperationalError):
                process_event(connection, make_event("order-1"))
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM processed_events").fetchone()[0], 0
            )

    def test_database_retry_is_bounded_and_exhaustion_surfaces(self):
        with patch("consumer.process_event", side_effect=sqlite3.OperationalError("locked")) as process:
            sleep = Mock()
            with self.assertRaises(sqlite3.OperationalError):
                process_with_retry(Mock(), make_event("order-1"), sleep=sleep)
            self.assertEqual(process.call_count, 3)
            self.assertEqual(sleep.call_count, 2)

    def test_dead_letter_preserves_binary_data_and_waits_for_delivery(self):
        message = Mock()
        message.topic.return_value = "orders"
        message.partition.return_value = 2
        message.offset.return_value = 7
        message.key.return_value = b"\xff"
        message.value.return_value = b"\x00\xff"
        message.headers.return_value = [("optional", None)]
        producer = Mock()
        dead_letter(producer, "orders.dlt", message, InvalidEvent("bad"))
        topic, key, body = producer.send.call_args.args
        envelope = json.loads(body)
        self.assertEqual(topic, "orders.dlt")
        self.assertEqual(key, b"orders:2:7")
        self.assertEqual(base64.b64decode(envelope["value_base64"]), b"\x00\xff")
        self.assertEqual(envelope["headers_base64"], [["optional", None]])
        producer.flush.assert_called_once()

    def test_producer_delivery_failure_is_not_reported_as_success(self):
        with patch("common.Producer") as client:
            client.return_value.flush.return_value = 0
            producer = ReliableProducer("unused:9092")
            producer._delivered("broker rejected record", Mock())
            with self.assertRaises(RuntimeError):
                producer.flush()

    def test_dead_letter_failure_does_not_commit_source_offset(self):
        message = Mock()
        message.error.return_value = None
        message.value.return_value = b"not-json"
        message.key.return_value = b"order-1"
        message.headers.return_value = []
        message.topic.return_value = "orders"
        message.partition.return_value = 0
        message.offset.return_value = 1
        with (
            patch("sys.argv", ["consumer.py", "--max-messages", "1"]),
            patch("consumer.open_store") as store,
            patch("consumer.Consumer") as client,
            patch("consumer.ReliableProducer") as producer,
        ):
            client.return_value.poll.return_value = message
            producer.return_value.flush.side_effect = RuntimeError("DLT unavailable")
            with self.assertRaisesRegex(RuntimeError, "DLT unavailable"):
                consume()
            client.return_value.commit.assert_not_called()
            client.return_value.close.assert_called_once()
            store.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
