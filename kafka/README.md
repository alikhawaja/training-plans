# Apache Kafka: from first event to enterprise patterns

Start with a gentle, diagram-led introduction to communicating applications and
events, then build an order-processing system while learning how Kafka stores,
distributes, replays, and protects event streams.

**Start with the [training guide](training-guide.md).** It contains the complete
walkthrough, commands, expected observations, and assessment.

## Prerequisites

- Basic Python and command-line knowledge; no prior Kafka or enterprise-system experience.
- Docker Engine or Docker Desktop running **Linux containers**, with Docker Compose
  v2.20 or newer. Follow your organization's Docker licensing and installation policy.
- Python 3.11-3.14 and `venv`. Examples are exercised with Python 3.13.
- Internet access to download the Apache Kafka image and Python dependency.
- Approximately 4 GB available container memory for one broker, or 8 GB for the
  three-broker lab; allow 10 GB free disk space. These are workshop budgets, not
  production sizing recommendations.
- Available loopback ports 9092, 19092, 29092, and 39092.

No host Java installation, ZooKeeper, cloud account, or paid Kafka service is required.
Commands use PowerShell on Windows; the guide gives POSIX-shell differences.

## Learning paths

| Path | Modules | Suggested time |
| --- | --- | --- |
| Foundations without running software | 1 | 90-120 minutes |
| First working application, including foundations | 1-4 | 4-5 hours, plus setup and breaks |
| Beginner workshop (recommended) | 1-12 and capstone | Three days |
| Compressed workshop for architecture-experienced learners | 1-12 and capstone | Two days with foundations prereading and selected demonstrations |
| Optional extensions | Connect, schemas, transactions, stream processing | Additional half to full day |

The beginner schedule places modules 1-4 on day 1, 5-9 on day 2, and 10-12 plus
the capstone on day 3. It includes review and troubleshooting time. Failure and
compaction labs deliberately require observation rather than instant results.

## Files

| Path | Purpose |
| --- | --- |
| [training-guide.md](training-guide.md) | Twelve sequenced modules and capstone |
| [infrastructure](infrastructure/) | Separate single-broker and three-broker Compose projects |
| [examples](examples/) | Topic setup, producer, consumer, SQLite deduplication, smoke check |
| [labs/enterprise-extensions.md](labs/enterprise-extensions.md) | Connect, schemas, transactions, and stream-processing follow-ons |
| [troubleshooting.md](troubleshooting.md) | Symptoms, causes, and recovery |
| [VALIDATION.md](VALIDATION.md) | Reproduction commands and recorded validation scope |

## Pinned baseline

Apache Kafka **4.1.2**, official JVM image `apache/kafka:4.1.2`, using KRaft.
Python client **confluent-kafka 2.12.2**. These are explicit workshop compatibility
pins, not a claim that they are the latest releases. The Confluent-maintained client
uses the Apache Kafka protocol; it does not require Confluent Platform.

## Safety boundaries

Both Compose projects bind client ports to `127.0.0.1`. They intentionally use
PLAINTEXT with no authentication or ACLs. Do not expose them to a network, deploy
them to production, or use real customer data. All brokers share one Docker host;
the resilience lab does **not** demonstrate host or availability-zone resilience.

Combined broker/controller roles and small heaps simplify local learning.
Production requires independent sizing, security, failure-domain design, monitoring,
backup/recovery planning, and supported upgrade procedures.
