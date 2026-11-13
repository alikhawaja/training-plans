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

From the repository root, after [preparing the virtual environment](environment-setup.md).
The readiness check is a **pre-start** check; existing workshop brokers must be
stopped without deleting their volumes first:

```bash
".venv/bin/python" kafka/examples/check_environment.py --profile single
docker compose -f kafka/infrastructure/compose.single.yml config --quiet
docker compose -f kafka/infrastructure/compose.cluster.yml config --quiet
".venv/bin/python" -m unittest discover -s kafka/examples -v
docker compose -f kafka/infrastructure/compose.single.yml up -d --wait --wait-timeout 180
".venv/bin/python" kafka/examples/smoke_test.py
```

<details>
<summary>PowerShell alternative (native Windows)</summary>

```powershell
.\.venv\Scripts\python.exe kafka\examples\check_environment.py --profile single
docker compose -f kafka\infrastructure\compose.single.yml config --quiet
docker compose -f kafka\infrastructure\compose.cluster.yml config --quiet
.\.venv\Scripts\python.exe -m unittest discover -s kafka\examples -v
docker compose -f kafka\infrastructure\compose.single.yml up -d --wait --wait-timeout 180
.\.venv\Scripts\python.exe kafka\examples\smoke_test.py
```

</details>

The smoke check uses a uniquely named temporary topic and deletes that topic when
finished, including on most failure paths. A failure before topic creation completes
may require inspecting topics manually. It does not erase the workshop topics.

Cluster smoke check:

```bash
docker compose -f kafka/infrastructure/compose.single.yml down
".venv/bin/python" kafka/examples/check_environment.py --profile cluster
docker compose -f kafka/infrastructure/compose.cluster.yml up -d --wait --wait-timeout 180
".venv/bin/python" kafka/examples/smoke_test.py --bootstrap localhost:19092,localhost:29092,localhost:39092 --replication-factor 3
docker compose -f kafka/infrastructure/compose.cluster.yml down
```

<details>
<summary>PowerShell alternative (native Windows)</summary>

```powershell
docker compose -f kafka\infrastructure\compose.single.yml down
.\.venv\Scripts\python.exe kafka\examples\check_environment.py --profile cluster
docker compose -f kafka\infrastructure\compose.cluster.yml up -d --wait --wait-timeout 180
.\.venv\Scripts\python.exe kafka\examples\smoke_test.py --bootstrap localhost:19092,localhost:29092,localhost:39092 --replication-factor 3
docker compose -f kafka\infrastructure\compose.cluster.yml down
```

</details>

Use modules 6-10 and extension A for interactive group, replay, failure, compaction,
and integration exercises. Expected failure commands are identified in the guide.

## Cross-platform acceptance

The dependency check found native Linux AMD64/ARM64 variants in the pinned Kafka
image manifest, and CPython 3.13 client wheels for macOS Intel/Apple Silicon,
glibc Linux AMD64/ARM64, and Windows AMD64. Image/wheel availability is **not**
evidence that a host's networking, terminal, Docker integration, or labs work.

| Target | Full host acceptance status |
| --- | --- |
| Windows 11 / Ubuntu LTS on WSL 2, AMD64 | Pending execution in a WSL terminal |
| Docker-supported macOS, Intel | Pending host execution |
| Docker-supported macOS, Apple Silicon | Pending host execution |
| Docker-supported Ubuntu LTS, AMD64 | Pending host execution |
| Docker-supported Ubuntu LTS, ARM64 | Pending host execution |
| Native Windows PowerShell, AMD64 (alternative) | Initial workshop evidence above; follow-up checks recorded below |

For **each target row separately**, record OS/distro release, CPU, shell, Python
patch and source, uv, Docker/Compose versions, Docker context/backend, resource
allocation, command output, and any adaptations. Use this same acceptance checklist:

1. Follow its installation path and create a fresh uv-managed Python 3.13
   environment; install the pinned native wheel without emulation/source builds.
2. Run preflight successfully before each profile; resolve resource warnings.
   Record a useful failure for a missing tool/dependency or occupied port, rather
   than treating process startup alone as success.
3. Pull the native Kafka image, start the single broker, and pass the nine-event
   smoke test. Verify console-producer piping and formatted consumption.
4. Run producer/consumer and SQLite inspection; reproduce crash/redelivery and
   deduplication, offset reset, and DLT behavior with the documented commands.
5. Initialize variables in separate terminals, observe group membership and
   rebalances, and confirm Ctrl+C closes clients without abandoning a process.
6. Observe retention/compaction with the stated asynchronous timing caveats.
7. Stop the single project preserving data; pass cluster preflight and the
   replication-factor-three smoke check; exercise one-broker outage/recovery.
8. Return to the single broker, run Connect source/sink and status commands,
   verify transferred lines and restart behavior, then stop its attached worker.
9. Verify non-destructive Compose shutdown/restart preserves data. Demonstrate
   volume deletion only on disposable acceptance data, with explicit intent;
   verify SQLite is separate. Remove only resources created for this acceptance run.

Do not mark a row passed from Windows-only execution, mocked unit tests, Bash
syntax checks, or an available multi-architecture manifest.

## Cross-platform update: follow-up observations

The update was checked on **2026-11-13** using native Windows 11 AMD64
(build 26300), PowerShell 7.7.0, uv 0.13.8, uv-managed CPython 3.13.18,
confluent-kafka 2.12.2 / librdkafka 2.12.1, and Docker Desktop's local
`desktop-linux` context. The Docker server reported Linux x86_64, Engine 29.9.2,
and Compose 5.6.1.

| Check | Observed result |
| --- | --- |
| Managed Python provisioning | Python 3.13 environment created with uv |
| Dependency restoration | Public package download hit a local TLS handshake failure, including with system trust; pinned wheel installed through the environment's preconfigured approved pip package index |
| Readiness, before installation | Missing client dependency reported explicitly; nonzero exit |
| Readiness, single/cluster | Both profiles passed with resource advisories |
| Readiness, broker already running | Port 9092 conflict reported explicitly; nonzero exit, no automatic shutdown |
| Unit tests | All 14 passed, including seven focused preflight tests and the original seven application tests |
| Command syntax | All 53 Bash blocks parsed with Bash; all 46 PowerShell blocks parsed with PowerShell |
| Image and Compose | Explicit pinned-image pull succeeded; both Compose configurations accepted |
| Single/cluster smoke tests | Both received all nine exact event IDs with per-key partition affinity and removed their unique topics |
| Cleanup | Only this run's previously absent Compose resources and newly created volumes were removed |

This was not a clean-machine installation test. uv/Git/Docker were already
installed, and the direct public-index uv dependency-download path was blocked
by the local network. uv does not automatically inherit pip configuration; see
the [approved-index and certificate guidance](troubleshooting.md#downloads-fail-behind-a-proxy-or-certificate-boundary).
The shell parsing checks do not execute installation or interactive labs.
WSL/macOS/native Ubuntu acceptance remains pending; no result above changes
those matrix rows to passed.

## Boundaries

- WSL/macOS/Linux commands are directly provided but full host acceptance remains
  pending as listed above.
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
