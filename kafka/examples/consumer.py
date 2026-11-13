"""Consume with explicit commits, SQLite deduplication, and a dead-letter topic."""

import argparse
import base64
import json
import sqlite3
import time
from pathlib import Path

from confluent_kafka import Consumer, KafkaException

from common import DEFAULT_BOOTSTRAP, InvalidEvent, ReliableProducer, decode_event, positive_int


def open_store(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS processed_events (
            event_id TEXT PRIMARY KEY, payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_totals (
            order_id TEXT PRIMARY KEY, event_count INTEGER NOT NULL
        );
        """
    )
    return connection


def process_event(connection, event):
    payload = json.dumps(event, sort_keys=True)
    with connection:
        previous = connection.execute(
            "SELECT payload FROM processed_events WHERE event_id = ?",
            (event["event_id"],),
        ).fetchone()
        if previous is not None:
            if previous[0] != payload:
                raise InvalidEvent("event_id reused with a different payload")
            return False
        connection.execute(
            "INSERT INTO processed_events VALUES (?, ?)", (event["event_id"], payload)
        )
        connection.execute(
            """INSERT INTO order_totals VALUES (?, 1)
               ON CONFLICT(order_id) DO UPDATE SET event_count = event_count + 1""",
            (event["order_id"],),
        )
    return True


def process_with_retry(connection, event, sleep=time.sleep):
    for attempt in range(3):
        try:
            return process_event(connection, event)
        except sqlite3.OperationalError as error:
            if attempt == 2:
                raise
            print(f"RETRY {attempt + 1}/2 after database error: {error}", flush=True)
            sleep(0.5 * (2**attempt))
    raise AssertionError("unreachable")


def dead_letter(producer, topic, message, error):
    # Base64 preserves malformed bytes and distinguishes empty data from null.
    def encoded(value):
        return None if value is None else base64.b64encode(value).decode("ascii")

    envelope = {
        "source_topic": message.topic(),
        "source_partition": message.partition(),
        "source_offset": message.offset(),
        "key_base64": encoded(message.key()),
        "value_base64": encoded(message.value()),
        "headers_base64": [
            [key, encoded(value)] for key, value in (message.headers() or [])
        ],
        "error": str(error),
    }
    key = f"{message.topic()}:{message.partition()}:{message.offset()}".encode("utf-8")
    producer.send(topic, key, json.dumps(envelope).encode("utf-8"))
    producer.flush()
    print(f"DEAD-LETTER source={key.decode('utf-8')} reason={error}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--topic", default="orders")
    parser.add_argument("--dlt", default="orders.dlt")
    parser.add_argument("--group", default="fulfillment")
    parser.add_argument("--db", default=".state/fulfillment.db")
    parser.add_argument("--max-messages", type=positive_int)
    parser.add_argument("--idle-timeout", type=positive_int, default=60)
    parser.add_argument("--commit-before-process", action="store_true")
    crash = parser.add_mutually_exclusive_group()
    crash.add_argument("--crash-before-process", action="store_true")
    crash.add_argument("--crash-after-process", action="store_true")
    args = parser.parse_args()
    if args.topic == args.dlt:
        parser.error("source topic and dead-letter topic must differ")
    connection = open_store(args.db)
    consumer = Consumer(
        {
            "bootstrap.servers": args.bootstrap,
            "broker.address.family": "v4",
            "group.id": args.group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
            "allow.auto.create.topics": False,
            "client.id": f"training-{args.group}",
        }
    )
    dlt_producer = ReliableProducer(args.bootstrap)
    count = 0
    last_message = time.monotonic()
    try:
        consumer.subscribe(
            [args.topic],
            on_assign=lambda _, partitions: print(
                f"ASSIGNED {[(p.topic, p.partition) for p in partitions]}", flush=True
            ),
            on_revoke=lambda _, partitions: print(
                f"REVOKED {[(p.topic, p.partition) for p in partitions]}", flush=True
            ),
        )
        while args.max_messages is None or count < args.max_messages:
            message = consumer.poll(1)
            if message is None:
                if time.monotonic() - last_message > args.idle_timeout:
                    raise TimeoutError(
                        "No record received within idle timeout; inspect topic/group/lag. "
                        "Use a larger --idle-timeout for an interactive lab."
                    )
                continue
            if message.error():
                raise KafkaException(message.error())
            last_message = time.monotonic()
            if args.commit_before_process:
                consumer.commit(message=message, asynchronous=False)
            if args.crash_before_process:
                raise RuntimeError("Injected failure before business processing")
            try:
                event = decode_event(message.value(), message.key())
                applied = process_with_retry(connection, event)
                print(
                    f"{'APPLIED' if applied else 'DUPLICATE'} "
                    f"event={event['event_id']} order={event['order_id']} "
                    f"partition={message.partition()} offset={message.offset()}",
                    flush=True,
                )
            except InvalidEvent as error:
                dead_letter(dlt_producer, args.dlt, message, error)
            if args.crash_after_process:
                raise RuntimeError("Injected failure after processing, before final commit")
            if not args.commit_before_process:
                consumer.commit(message=message, asynchronous=False)
            count += 1
    except KeyboardInterrupt:
        print("Interrupted; closing consumer without committing unprocessed records.")
    finally:
        consumer.close()
        connection.close()


if __name__ == "__main__":
    main()
