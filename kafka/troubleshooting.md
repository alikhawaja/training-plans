# Kafka workshop troubleshooting

Commands assume the variables and working directory from the
[training guide](training-guide.md#prerequisites-and-command-conventions).
Preserve logs before changing configuration. Do not delete volumes as a first response.
Use Bash on WSL, macOS, and Linux; expandable alternatives are for native Windows
PowerShell. Start with the [pre-start readiness check](environment-setup.md#readiness-gate-then-start-the-lab).

## WSL integration or Docker permissions fail

On Windows, confirm `wsl --list --verbose` reports version 2 for the distribution.
In Docker Desktop, select the WSL 2 engine, Linux containers, and integration
with that distribution. Open a new Ubuntu terminal after changing integration.
Do not install a second Docker daemon inside WSL to work around missing integration.
On native Ubuntu, check daemon status and approved user access; Docker-group
changes require a new login. Do not use a world-writable socket.

In the workshop terminal:

```bash
docker context show
docker context inspect
docker info
```

<details>
<summary>PowerShell alternative (native Windows)</summary>

```powershell
docker context show
docker context inspect
docker info
```

</details>

The daemon must be local and report Linux containers. Remove unintended
`DOCKER_HOST`/`DOCKER_CONTEXT` overrides using your shell's environment settings,
or select the correct local context after inspection. Do not change unrelated
Docker projects or contexts blindly. WSL integration, Windows port reservations,
VPN/firewall rules, and endpoint protection can affect loopback connectivity.
Use the smoke test **inside the same Ubuntu terminal** as the labs; native Windows
success does not prove WSL connectivity. Follow approved WSL/Docker networking
guidance rather than opening Kafka listeners to the LAN.

## Downloads fail behind a proxy or certificate boundary

Git, uv, managed Python, and Docker image pulls use different download paths and
may need separate approved proxy/CA configuration. Inspect the reported URL and
TLS error. For uv, use its
[certificate configuration](https://docs.astral.sh/uv/concepts/authentication/certificates/)
and your organization's trust store (current uv supports `--system-certs`).
A TLS handshake failure is not necessarily a missing CA; consult the proxy/network
administrator if using the system trust store does not help.
uv does not read pip's configuration files. If your organization requires a package
mirror, configure that approved [index in uv](https://docs.astral.sh/uv/concepts/indexes/)
as well; an existing pip setup alone does not configure uv.

For restricted networks, an instructor can distribute approved, hash-verified
wheels matching the pinned version, Python, OS, and CPU, and a preloaded Kafka
image. uv can install approved local wheels without contacting an index.
Do not use `--allow-insecure-host`, disable certificate verification, or switch
to an untrusted mirror. Preflight does not test download access: the explicit
dependency installation and image-pull steps do.

## Broker does not become healthy

```bash
docker info
docker compose -f "$Single" ps -a
docker compose -f "$Single" logs --tail 100 kafka
```

<details>
<summary>PowerShell alternative (native Windows)</summary>

```powershell
docker info
docker compose -f $Single ps -a
docker compose -f $Single logs --tail 100 kafka
```

</details>

Start Docker Engine/Desktop if the daemon is unavailable, and select Linux
containers on Windows. Check free disk, Docker memory allocation, image-download
access, and port conflicts. An image pull error is not a broker configuration error.
On slow machines retry `up -d --wait --wait-timeout 300` after checking logs.

For the cluster, substitute `$Cluster` and inspect `broker-1`, `broker-2`, and
`broker-3`. A metadata quorum requires a majority of controllers.

## Address already in use

Another application may own port 9092, 19092, 29092, or 39092. Identify it before
stopping anything:

On WSL/Ubuntu, inspect the selected port with `ss`:

```bash
ss -ltnp 'sport = :9092'
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

On macOS:

```bash
lsof -nP -iTCP:9092 -sTCP:LISTEN
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

On native Windows (or for a Windows-side listener affecting WSL):

```powershell
Get-NetTCPConnection -LocalPort 9092 -State Listen
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

Do not terminate unrelated processes. If you change published ports, update both
the corresponding advertised EXTERNAL address and client `--bootstrap` addresses.

## Bootstrap connects but clients cannot send or read

The host uses `localhost:9092` for the single node or the three external cluster
ports. Container-side commands use `kafka:19092` or `broker-1:9092`.
Inspect `KAFKA_ADVERTISED_LISTENERS`: clients must reach the returned addresses.
Do not use the controller listener for application traffic.

The examples are designed for a client on this Docker host, not a remote machine.
Do not solve remote access by publishing insecure ports to all interfaces.
The Python clients explicitly resolve broker addresses as IPv4, matching the
Compose loopback binding and avoiding failed IPv6 `localhost` attempts on Windows.

## Unknown topic or timeout while producing

```bash
"$Python" kafka/examples/topics.py
docker compose -f "$Single" exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:19092 --list
```

<details>
<summary>PowerShell alternative (native Windows)</summary>

```powershell
& $Python kafka\examples\topics.py
docker compose -f $Single exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:19092 --list
```

</details>

Topic auto-creation is disabled deliberately. For the cluster, pass all three host
bootstrap addresses and `--replication-factor 3` to `topics.py`.
Check final delivery errors, not only temporary broker connection messages.

## Consumer waits, then raises an idle timeout

The default idle timeout is 60 seconds; use `--idle-timeout 600` for an interactive
session. `--max-messages` counts records received by **this process**, not the whole
group, and includes invalid records successfully quarantined.

An existing group resumes its commits; `earliest` does not force replay. Another
member may own the relevant partition. Inspect the group, produce more events, or
use a fresh group and database. Do not ask for more records than are available.

## Reset offsets fails or appears ineffective

Stop **all** members of that group, verify its state with `kafka-consumer-groups.sh`,
preview with `--dry-run`, and only then use `--execute`. Reset the correct topic
on the correct cluster. Consumers may print `DUPLICATE` after a successful reset
because the downstream deduplication database still contains the event IDs.

## Duplicate output after a restart

Redelivery is expected with at-least-once consumption. `DUPLICATE` means the SQLite
deduplication guard worked. Running the producer again creates new event IDs and
therefore new business events; those should be applied.

If different consumers should perform independent effects, give them different
groups **and** databases. SQLite deduplication is not automatic payment/email
deduplication and is not shared across different host-local files.

## Database locked or unable to open database

Use a writable local directory, not a network filesystem. Brief contention is
retried; repeated failures surface and leave the Kafka record uncommitted.
The shared SQLite lab is intentionally small. Real distributed consumers need
a suitable shared durable store and transaction/idempotency design.

## DLT cannot be written

Confirm `orders.dlt` exists, has available replicas, and is not the source topic.
The default consumer must not commit an invalid source record until DLT delivery
is acknowledged. Repair the underlying failure and restart; do not skip offsets
just to clear the error. DLT duplicates are possible after a crash.

## Compaction has not removed old versions

Compaction is not synchronous. Check the cleanup policy, segment rolling, dirty
ratio, and cleaner scheduling. A quiet active segment may need a new append after
the segment-roll interval. Allow minutes, not milliseconds. Console consumers may
time out before `--max-messages` if cleaning has already removed some records.

## Writes fail during cluster outage

With replication factor 3 and minimum ISR 2, one healthy in-sync replica is
insufficient for `acks=all`. This combined-role lab also loses controller quorum
when two nodes are down. Restore nodes and inspect ISR before retrying.
Do not lower durability settings to make the lab "pass."

## Python dependency missing

Use the same virtual environment for installation and execution:

```bash
uv pip install --python ".venv/bin/python" --only-binary=:all: -r kafka/examples/requirements.txt
".venv/bin/python" -m unittest discover -s kafka/examples -v
```

<details>
<summary>PowerShell alternative (native Windows)</summary>

```powershell
uv pip install --python .\.venv\Scripts\python.exe --only-binary=:all: -r kafka\examples\requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s kafka\examples -v
```

</details>

If a wheel is unavailable for your Python/platform combination, use a supported
native 64-bit CPython 3.13 environment as described in
[setup](environment-setup.md). Binary-only installation intentionally refuses
unsupported combinations. Do not install random binary packages.

## Workshop counts differ on a repeated run

The walkthrough's initial counts assume a fresh sequence. Existing records,
additional producer invocations, group commits, and SQLite files persist separately.
Inspect state before proceeding. Choose new scratch topics/groups/databases for
an isolated retry, or use the explicitly destructive cleanup instructions only
when you intend to erase the Kafka lab data.
