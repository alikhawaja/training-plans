"""Create workshop topics; reject existing topics with an unexpected topology."""

import argparse

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

from common import DEFAULT_BOOTSTRAP


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--replication-factor", type=int, choices=(1, 3), default=1)
    args = parser.parse_args()
    admin = AdminClient(
        {"bootstrap.servers": args.bootstrap, "broker.address.family": "v4"}
    )
    minimum_isr = 2 if args.replication_factor == 3 else 1
    configs = {
        "orders": {"cleanup.policy": "delete", "retention.ms": "604800000"},
        "orders.dlt": {"cleanup.policy": "delete", "retention.ms": "604800000"},
        "order-status": {"cleanup.policy": "compact", "delete.retention.ms": "60000"},
    }
    futures = admin.create_topics(
        [
            NewTopic(
                name,
                num_partitions=3,
                replication_factor=args.replication_factor,
                config={**config, "min.insync.replicas": str(minimum_isr)},
            )
            for name, config in configs.items()
        ],
        request_timeout=30,
    )
    for name, future in futures.items():
        try:
            future.result()
            print(f"CREATED {name}")
        except KafkaException as error:
            if error.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
                raise
            print(f"EXISTS {name}; checking partitions and replicas")
    metadata = admin.list_topics(timeout=30)
    for name in configs:
        topic = metadata.topics[name]
        if topic.error:
            raise KafkaException(topic.error)
        if len(topic.partitions) != 3 or any(
            len(partition.replicas) != args.replication_factor
            for partition in topic.partitions.values()
        ):
            raise RuntimeError(f"{name}: topology differs; inspect it before proceeding")
    print("READY; existing topic configuration is not overwritten. Inspect configs if reused.")


if __name__ == "__main__":
    main()
