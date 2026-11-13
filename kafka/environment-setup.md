# Prepare the Kafka workshop environment

Complete this page before module 2. Everyone uses the same Linux Kafka image,
Python client, lab commands, and expected results. Only tool installation differs.
The [validation record](VALIDATION.md) distinguishes available dependencies from
platforms on which the full workshop has actually been exercised.

## Supported workshop targets

| Your computer | Workshop terminal | Container runtime |
| --- | --- | --- |
| Windows 11, x64 | Bash inside an Ubuntu LTS **WSL 2** distribution | Docker Desktop with the WSL 2 backend and that distribution's integration enabled |
| Docker-supported macOS, Intel | Bash (`bash` in Terminal) | Docker Desktop for Intel |
| Docker-supported macOS, Apple Silicon | Native ARM64 Bash (`bash` in Terminal) | Docker Desktop for Apple Silicon |
| Docker-supported Ubuntu LTS, AMD64 or ARM64 | Bash | Docker Engine with the Compose plugin |

Use maintained OS releases that meet the linked Docker installation requirements.
Ubuntu 24.04 LTS is a common baseline for both WSL and native Linux; use Docker's
supported-version list when selecting another LTS. Windows ARM, Windows Server,
other Linux distributions, remote Docker hosts, Podman, and alternative desktop
runtimes are not covered by this baseline.

The pinned `apache/kafka:4.1.2` image has Linux AMD64 and ARM64 variants.
`confluent-kafka==2.12.2` has CPython 3.13 wheels for macOS Intel/Apple Silicon
(macOS 13 or later) and glibc Linux AMD64/ARM64 (glibc 2.28 or later).
Use your machine's native architecture; do not add `platform: linux/amd64` on
Apple Silicon. Rosetta is not required by this native workshop path.

### Capacity, access, and safety

- Allow **4 GB available to containers** for the single broker, or **8 GB** for
  the three-broker lab. These are workshop budgets, not measured production sizing.
  Leave additional RAM for the host OS, Python, and your editor; a machine with
  16 GB total RAM is a practical recommendation for the complete workshop, not a
  guarantee. Stop the single-broker project before starting the cluster.
- Allow **10 GiB free lab storage**, plus headroom for tool installation, image
  downloads, and the OS. Check both the checkout disk and Docker's backing
  disk/VM storage. Docker-visible RAM and virtual-disk capacity do not necessarily
  equal resources currently available on the physical host.
- Enable hardware virtualization for Docker Desktop/WSL. If already inside a VM,
  your administrator must provide supported nested virtualization.
- Single-broker host port: **9092**. Cluster host ports: **19092, 29092, 39092**.
  All are IPv4 loopback-only. Kafka's internal port 19092 in the single-broker
  container is not a second published host port.
- Arrange permissions for OS features, approved software installation, and Docker
  access before the workshop. Follow your organization's Docker Desktop
  [licensing](https://docs.docker.com/subscription/desktop-license/) policy.
- Downloads require HTTPS access to GitHub (repository, uv, managed Python),
  Docker Hub and its image storage endpoints, and PyPI/Python package storage.
  Initial OS/tool installation also needs the relevant Microsoft, Apple, or
  Ubuntu software sources.
  Configure approved proxy and CA settings for the host, uv, and Docker separately.
  Never disable TLS verification or use unapproved binary mirrors to bypass policy.
- Use a **local** Docker daemon and a writable local checkout, not a network or
  cloud-synchronized directory. Keep SQLite on that local filesystem. Do not copy
  virtual environments between Windows, WSL, machines, or CPU architectures.

No host Java, ZooKeeper, cloud account, or paid Kafka service is needed. The
containers have deliberately insecure local-only Kafka listeners; use synthetic
data and never publish them to your LAN.

## Windows 11: prepare WSL first

These are **Windows PowerShell host setup** commands, not lab commands:

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
wsl --list --verbose
```

The initial WSL installation may require an elevated terminal, a restart, and
creating a Linux user. If Ubuntu is already installed, inspect it rather than
reinstalling it. Its version in `wsl --list --verbose` must be **2**, not 1.
See [Microsoft's WSL installation guide](https://learn.microsoft.com/windows/wsl/install)
and [Docker's Windows requirements](https://docs.docker.com/desktop/setup/install/windows-install/).

Install and start Docker Desktop for Windows x64 using the official installer.
Select **Use WSL 2 based engine**, Linux containers, and
**Settings > Resources > WSL Integration > Ubuntu-24.04** (or your selected distro).
Follow [Docker's WSL integration instructions](https://docs.docker.com/desktop/features/wsl/).
Do not install another Docker Engine inside that distro.

**From this point, open Ubuntu and use its Bash terminal**, including for Git,
uv, Python, and every new workshop terminal:

```bash
sudo apt update
sudo apt install git curl ca-certificates
docker info
docker compose version
```

Clone under your Linux home directory, not a mounted Windows drive. This keeps
Python, Git, and SQLite in one filesystem and avoids mixing Windows executables
with Linux ones. A Windows editor may connect through its WSL support.

## macOS: prepare native tools

Install and start [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
for **your CPU**. Docker supports the current and two preceding major macOS
releases; check its current requirements. Accept any required OS approvals.

Install Git with Apple's command-line tools if it is not already available:

```bash
xcode-select --install
```

Complete the installer before continuing. Open Terminal and start Bash explicitly
(the default interactive shell may be Zsh):

```bash
bash
uname -m
git --version
docker info
docker compose version
```

Expect `arm64` on Apple Silicon or `x86_64` on Intel. On Apple Silicon, use a
native terminal, not a Rosetta-launched one. Do not use Apple's system Python for
the virtual environment.

## Ubuntu LTS: prepare Docker Engine

Install Git and the HTTPS tools:

```bash
sudo apt update
sudo apt install git curl ca-certificates
```

Follow [Docker's official Ubuntu installation steps](https://docs.docker.com/engine/install/ubuntu/)
for the Docker apt repository, Engine, and **docker-compose-plugin**. Use
`docker compose`, not legacy `docker-compose`. Do not mix conflicting distribution,
Desktop, and Engine installations. This Engine installation is for native Ubuntu,
**not** the Docker Desktop-integrated WSL path above.

Arrange access so ordinary `docker` commands work in the workshop terminal.
Docker's [Linux post-install guide](https://docs.docker.com/engine/install/linux-postinstall/)
explains the Docker group and logging out/in after membership changes.
**Docker-group membership grants root-equivalent privileges**; obtain organizational
approval. Never make the Docker socket world-writable. Do not run uv or Python
with `sudo` or create root-owned workshop files.

```bash
docker info
docker compose version
```

If these fail, fix daemon startup or user access before proceeding.

## Shared Bash setup: Windows/WSL, macOS, and Linux

Install [uv using its official instructions](https://docs.astral.sh/uv/getting-started/installation/).
For the standalone installer, download and review it before execution:

```bash
Installer="$(mktemp)"
curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh -o "$Installer" &&
  less "$Installer" &&
  sh "$Installer"
rm "$Installer"
```

Use `q` to leave the installer review. Open a new Bash terminal afterward so the
updated PATH is available, then verify `uv --version`. Use an organization-approved
installation method if remote installers are restricted.

uv's managed CPython comes from Astral's `python-build-standalone` distributions,
not an OS package or a python.org installer. See
[uv's Python installation documentation](https://docs.astral.sh/uv/guides/install-python/).
The following explicitly selects **3.13**, rather than the OS default:

```bash
mkdir -p "$HOME/kafka-workshop"
cd "$HOME/kafka-workshop"
git clone https://github.com/alikhawaja/training-plans.git
cd training-plans
uv python install 3.13
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python --only-binary=:all: -r kafka/examples/requirements.txt
```

If you already have this repository in a suitable local directory, use it instead
of cloning again. For an existing `.venv` from a different OS/version, use a fresh
checkout rather than deleting an environment that might belong to other work.
Binary-only installation deliberately fails if no compatible client wheel is
available; do not begin an unplanned native-library build.

Run **all remaining commands from the repository root**. Set these variables in
**every new Bash terminal**, including consumer and Connect terminals:

```bash
Python=".venv/bin/python"
Single="kafka/infrastructure/compose.single.yml"
Cluster="kafka/infrastructure/compose.cluster.yml"
"$Python" --version
```

No activation is needed. All guide commands use the virtual environment directly.
Paths such as `/opt/kafka/bin/...` refer to the Linux container, not the host.

### Native Windows PowerShell alternative

The recommended Windows path remains WSL. The guide also retains the original
native Windows client route for learners using an approved Windows x64 Python
environment. Keep its checkout and `.venv` separate from WSL. Install Git, uv,
and Docker Desktop using their official Windows installers; keep Linux containers
enabled. In PowerShell, from the repository root:

```powershell
uv python install 3.13
uv venv --python 3.13 .venv
uv pip install --python .\.venv\Scripts\python.exe --only-binary=:all: -r kafka\examples\requirements.txt
$Python = ".\.venv\Scripts\python.exe"
$Single = "kafka\infrastructure\compose.single.yml"
$Cluster = "kafka\infrastructure\compose.cluster.yml"
& $Python --version
```

Set the three variables in every new PowerShell terminal. Use the guide's
**PowerShell alternatives**, not Bash syntax. No execution-policy changes or
virtual-environment activation are needed.

## Readiness gate, then start the lab

Before starting containers, run the preflight from the same terminal as the labs:

```bash
"$Python" kafka/examples/check_environment.py --profile single
```

<details>
<summary>PowerShell alternative (native Windows)</summary>

```powershell
& $Python kafka\examples\check_environment.py --profile single
```

</details>

The preflight reports interpreter/client versions, Docker/Compose/context,
configuration, local SQLite writes, ports, and resource advisories. A blocking
failure returns a nonzero exit code. It makes no system changes: its temporary
SQLite probe is removed, and it does not pull images or start/delete containers.
Resource warnings require checking Docker's backing disk/VM allocation yourself.
Run it with `--profile cluster` after stopping the single-broker environment and
before module 10. An already-running broker occupies its own ports: stop only
your workshop project, preserving volumes, before rerunning this **pre-start** check.

Once prerequisites pass, explicitly download the image, start Kafka, and exercise
real client connectivity:

```bash
docker compose -f "$Single" pull
docker compose -f "$Single" up -d --wait --wait-timeout 180
"$Python" kafka/examples/smoke_test.py
```

<details>
<summary>PowerShell alternative (native Windows)</summary>

```powershell
docker compose -f $Single pull
docker compose -f $Single up -d --wait --wait-timeout 180
& $Python kafka\examples\smoke_test.py
```

</details>

Expect a healthy broker and `PASS: nine exact event IDs received; each key stayed
in one partition.` The smoke test creates/deletes only its unique temporary topic.
It does not preload the workshop's `orders` topic. Leave the broker running and
continue with [module 2](training-guide.md#2-run-kafka-in-a-container-30-minutes).
If any step fails, use [troubleshooting](troubleshooting.md); do not change
loopback listeners or disable security checks as a workaround.
