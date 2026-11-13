"""Shared event contract and acknowledged delivery for the workshop."""

import argparse
import json
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer

DEFAULT_BOOTSTRAP = "localhost:9092"
STATUSES = ("created", "paid", "shipped")


class InvalidEvent(ValueError):
    pass


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def make_event(order_id, status="created"):
    return {
        "event_id": str(uuid.uuid4()),
        "schema_version": 1,
        "order_id": order_id,
        "status": status,
        "amount_cents": 1250,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }


def decode_event(value, key):
    try:
        event = json.loads(value)
    except (ValueError, TypeError, UnicodeDecodeError) as error:
        raise InvalidEvent("value must be UTF-8 JSON, not a tombstone") from error
    if not isinstance(event, dict):
        raise InvalidEvent("event must be a JSON object")
    for field in ("event_id", "order_id", "occurred_at"):
        if not isinstance(event.get(field), str) or not event[field].strip():
            raise InvalidEvent(f"{field} must be a non-empty string")
    if type(event.get("schema_version")) is not int or event["schema_version"] != 1:
        raise InvalidEvent("only integer schema_version 1 is supported")
    if event.get("status") not in STATUSES:
        raise InvalidEvent(f"status must be one of {STATUSES}")
    if type(event.get("amount_cents")) is not int or event["amount_cents"] < 0:
        raise InvalidEvent("amount_cents must be a non-negative integer")
    try:
        occurred_at = datetime.fromisoformat(event["occurred_at"])
    except ValueError as error:
        raise InvalidEvent("occurred_at must be an ISO 8601 timestamp") from error
    if occurred_at.tzinfo is None:
        raise InvalidEvent("occurred_at must include a timezone")
    if key != event["order_id"].encode("utf-8"):
        raise InvalidEvent("record key must match order_id")
    return event


class ReliableProducer:
    def __init__(self, bootstrap):
        self.client = Producer(
            {
                "bootstrap.servers": bootstrap,
                "broker.address.family": "v4",
                "enable.idempotence": True,
                "acks": "all",
                "delivery.timeout.ms": 30000,
                "client.id": "training-producer",
            }
        )
        self.errors = []

    def _delivered(self, error, message):
        if error is not None:
            self.errors.append(str(error))
        else:
            print(
                f"DELIVERED {message.topic()} partition={message.partition()} "
                f"offset={message.offset()} key={message.key()!r}",
                flush=True,
            )

    def send(self, topic, key, value, headers=None):
        self.client.produce(
            topic, key=key, value=value, headers=headers, on_delivery=self._delivered
        )
        self.client.poll(0)

    def flush(self):
        remaining = self.client.flush(35)
        if self.errors or remaining:
            raise RuntimeError(
                f"delivery failed: errors={self.errors}, pending={remaining}"
            )
