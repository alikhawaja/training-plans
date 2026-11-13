"""Produce valid orders, deliberately invalid records, or compaction tombstones."""

import argparse
import json

from common import DEFAULT_BOOTSTRAP, STATUSES, ReliableProducer, make_event, positive_int


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--topic", default="orders")
    parser.add_argument("--count", type=positive_int, default=9)
    parser.add_argument("--order-id")
    parser.add_argument("--status", choices=STATUSES, default="created")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--invalid", action="store_true", help="send non-JSON test data")
    mode.add_argument("--tombstone", action="store_true", help="send a null value")
    args = parser.parse_args()
    if args.tombstone and not args.order_id:
        parser.error("--tombstone requires an explicit --order-id")
    producer = ReliableProducer(args.bootstrap)
    for index in range(args.count):
        order_id = args.order_id or f"order-{index % 3 + 1}"
        value = json.dumps(make_event(order_id, args.status)).encode("utf-8")
        if args.invalid:
            value = b"deliberately-not-json"
        elif args.tombstone:
            value = None
        producer.send(
            args.topic, order_id.encode("utf-8"), value, [("event-type", b"order.status")]
        )
    producer.flush()


if __name__ == "__main__":
    main()
