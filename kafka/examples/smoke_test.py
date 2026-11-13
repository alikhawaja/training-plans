"""Create an isolated temporary topic, verify keyed delivery, then delete it."""

import argparse
import json
import time
import uuid

from confluent_kafka import Consumer, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

from common import DEFAULT_BOOTSTRAP, ReliableProducer, decode_event, make_event


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--replication-factor", type=int, choices=(1, 3), default=1)
    args = parser.parse_args()
    topic = f"training-smoke-{uuid.uuid4().hex}"
    admin = AdminClient(
        {"bootstrap.servers": args.bootstrap, "broker.address.family": "v4"}
    )
    admin.create_topics(
        [NewTopic(topic, 3, args.replication_factor)], request_timeout=30
    )[topic].result()
    consumer = None
    try:
        producer = ReliableProducer(args.bootstrap)
        events = [make_event(f"smoke-{index % 3}") for index in range(9)]
        for event in events:
            producer.send(
                topic, event["order_id"].encode("utf-8"), json.dumps(event).encode("utf-8")
            )
        producer.flush()
        consumer = Consumer(
            {
                "bootstrap.servers": args.bootstrap,
                "broker.address.family": "v4",
                "group.id": topic,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        consumer.subscribe([topic])
        seen = set()
        partitions_by_key = {}
        deadline = time.monotonic() + 60
        while len(seen) < len(events) and time.monotonic() < deadline:
            message = consumer.poll(1)
            if message is None:
                continue
            if message.error():
                raise KafkaException(message.error())
            event = decode_event(message.value(), message.key())
            seen.add(event["event_id"])
            partitions_by_key.setdefault(event["order_id"], set()).add(message.partition())
        expected = {event["event_id"] for event in events}
        if seen != expected or any(len(parts) != 1 for parts in partitions_by_key.values()):
            raise RuntimeError(f"smoke check failed: received={seen}, partitions={partitions_by_key}")
        print("PASS: nine exact event IDs received; each key stayed in one partition.")
    finally:
        if consumer is not None:
            consumer.close()
        admin.delete_topics([topic], operation_timeout=30)[topic].result()
        print(f"DELETED temporary topic {topic}")


if __name__ == "__main__":
    main()
