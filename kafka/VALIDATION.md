# Validation and reproduction

## Recorded scope

The initial workshop was exercised on **2026-11-13**, using Windows PowerShell,
Python 3.13, Docker Desktop with Linux containers, Apache Kafka 4.1.2, and
confluent-kafka 2.12.2.

| Area | Observed result |
| --- | --- |
| Both Compose files | Configuration accepted; all four brokers became healthy |
| Single-broker smoke check | All nine exact event IDs received; repeated keys stayed in one partition |
| Python business consumer | Nine valid records applied to SQLite with explicit commits |
| Failure after processing | Restart redelivered the event; SQLite effect was not repeated |
| Commit before processing | Injected failure left no database effect; group skipped the committed record |
| Invalid event | Original bytes and source coordinates reached the DLT before source commit |
| Independent subscription | Separate group/database processed the retained event independently |
| Offset reset | Reset to earliest caused replay; durable deduplication prevented repeated effects |
| Console tools | Documented PowerShell key/value piping and formatted consumption worked |
| Persistence | Topic metadata and partition topology survived container removal/recreation without deleting its volume |
| Compaction | Topic overrides accepted; older versions were removed, leaving the latest closed-segment value and active-segment tombstone |
| Three-broker smoke check | Replication-factor-three topic accepted and returned all nine exact event IDs |
| One-broker outage | Nine records acknowledged and consumed with two ISR members; recovered node rejoined ISR |
| Two-broker outage | Producer failed explicitly after its delivery timeout; no false success |
| Kafka Connect | File source and sink connector/tasks reported RUNNING; two lines reached the sink file |
| Focused unit tests | Seven tests covering validation, rollback, deduplication, bounded retries, delivery failure, DLT bytes, and source-commit safety |

The Python clients explicitly use IPv4 to match the loopback port bindings.
Assignment logging formats partition attributes rather than the pinned client's
native partition-object representation, which fails on the tested Windows build.

## Reproduce the smallest checks

From the repository root, after preparing the virtual environment:

```powershell
docker compose -f kafka\infrastructure\compose.single.yml config --quiet
docker compose -f kafka\infrastructure\compose.cluster.yml config --quiet
.\.venv\Scripts\python.exe -m unittest discover -s kafka\examples -v
docker compose -f kafka\infrastructure\compose.single.yml up -d --wait --wait-timeout 180
.\.venv\Scripts\python.exe kafka\examples\smoke_test.py
```

The smoke check uses a uniquely named temporary topic and deletes that topic when
finished, including on most failure paths. A failure before topic creation completes
may require inspecting topics manually. It does not erase the workshop topics.

Cluster smoke check:

```powershell
docker compose -f kafka\infrastructure\compose.single.yml down
docker compose -f kafka\infrastructure\compose.cluster.yml up -d --wait --wait-timeout 180
.\.venv\Scripts\python.exe kafka\examples\smoke_test.py --bootstrap localhost:19092,localhost:29092,localhost:39092 --replication-factor 3
docker compose -f kafka\infrastructure\compose.cluster.yml down
```

Use modules 6-10 and extension A for interactive group, replay, failure, compaction,
and integration exercises. Expected failure commands are identified in the guide.

## Boundaries

- macOS/Linux command adaptations are provided but were not executed on those hosts.
- Exact compaction timing and eventual tombstone removal are not asserted by the
  smoke test; the guide explains asynchronous segment and cleaner behavior.
- Multi-process group membership/rebalance observations are learner exercises, not
  part of the nine-message automated smoke check.
- TLS, ACLs, schema-registry enforcement, CDC, transactions, and stream processing
  are discussed or assigned as follow-on designs, not claimed as deployed features.
- These checks establish local workshop behavior, not performance, security,
  cross-host resilience, production readiness, or an end-to-end exactly-once guarantee.

Containers and validation-created volumes/databases were removed after the initial
checks so the first learner run starts without preloaded workshop events. The
virtual environment remains available locally and is excluded from version control.
