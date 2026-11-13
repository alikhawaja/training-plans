# REST APIs: from a request to an enterprise service

Learn what an API is before building one. Begin with a gentle, diagram-led
introduction to clients, servers, HTTP, and REST, then build and use an order API.

**Start with the [training guide](training-guide.md).** It includes explanations,
commands, expected responses, failure exercises, and a capstone.

## Before you begin

The workshop provides Windows, macOS, and Linux instructions. Basic Python and
terminal familiarity are assumed; web and enterprise-system knowledge are not.
The conceptual introduction needs no software installation.

| Requirement | Who needs it? | Check |
| --- | --- | --- |
| Python 3.11-3.13, with pip and venv | All hands-on learners, including those using a container server | Windows: `python --version`; macOS/Linux: `python3 --version` |
| A terminal and shell | All hands-on learners | Windows PowerShell 5.1 or PowerShell 7+; macOS Terminal with zsh/bash; Linux terminal with bash |
| A browser | All hands-on learners | Can open local addresses and Swagger UI |
| Git | Only when obtaining the repository with `git clone` | `git --version`; downloading and extracting the repository ZIP is an alternative |
| curl | The command-line comparison exercises in modules 4 and 7 | Windows: `curl.exe --version`; macOS/Linux: `curl --version` |
| Docker running Linux containers and Compose v2.20+ | Only the Docker server path | `docker info` and `docker compose version` |

**PowerShell is not required on macOS or Linux.** Windows Terminal is a terminal
application, not a shell: select its PowerShell profile, not Command Prompt.
On macOS/Linux use bash or zsh, not fish, for the supplied shell commands.
The Python/HTTPX exercises themselves are identical on all three platforms.

Choose **one** server path: native Python (no Docker required), or Docker.
Both use host Python for the client and tests. The container uses Python 3.13.
Allow about 2 GB free disk space for the small lab, plus Docker's own installation
requirements if selected, and approximately 1 GB available container memory.
Port 8000 on loopback must be available. Internet access is needed for packages,
container images if selected, and Swagger UI's externally hosted assets.
No cloud account is required.

### Install missing tools

Use official installers or your operating system's package manager. Complete any
administrator-approved installation before class; reopen your terminal afterward.

| Platform | Python, shell, Git, and curl | Optional container server |
| --- | --- | --- |
| Windows | Install [Python 3.13](https://www.python.org/downloads/windows/) with pip and add Python to PATH. Windows PowerShell is built in; [PowerShell 7](https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows) is optional. Install [Git for Windows](https://git-scm.com/downloads/win). Current Windows includes `curl.exe`; if absent, use an official [curl distribution](https://curl.se/download.html). | Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) and follow its WSL 2/virtualization requirements. Start Docker Desktop and select Linux containers. |
| macOS | Install a supported Python version from [python.org](https://www.python.org/downloads/macos/); do not rely on Apple's system Python. Terminal and zsh are built in. Install [Git](https://git-scm.com/downloads/mac) if needed; curl normally ships with macOS. | Install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/), choosing Apple silicon or Intel to match your machine, and start it. |
| Linux | Use your distribution's packages for Python 3.11-3.13, pip, venv, Git, and curl. On Ubuntu/Debian, when the default Python is supported: `sudo apt update` then `sudo apt install python3 python3-pip python3-venv git curl`. Other distributions use different package names; check the version before creating a venv. | Follow [Docker Engine installation](https://docs.docker.com/engine/install/) for your distribution and install the [Compose plugin](https://docs.docker.com/compose/install/linux/). Follow approved Docker access setup; Docker daemon access is privileged. |

If `python`/`python3` selects an unsupported version, use your installed supported
executable (for example `py -3.13` on Windows or `python3.13` on macOS/Linux) to
create the virtual environment. Do not replace your operating system's Python.
See the [Python venv documentation](https://docs.python.org/3/library/venv.html)
if your distribution packages venv separately.

Follow [environment preparation](training-guide.md#environment-preparation)
for repository download, per-shell commands, and a readiness checkpoint before
the practical modules. Do not skip setup because Docker is already installed.

## Learning paths

| Path | Modules | Suggested time |
| --- | --- | --- |
| Foundations without software | 1 | 90-120 minutes |
| First API and client | 1-4 | One beginner-paced day |
| Complete beginner workshop | 1-12 and capstone | Three days |
| Experienced developer path | 1-12 and capstone | Two days with foundations prereading |
| Optional extensions | [Enterprise exercises](labs/enterprise-extensions.md) | Additional half to full day |

Allow time for discussion and troubleshooting, not only command execution.

## Files and technology

| Path | Purpose |
| --- | --- |
| [training-guide.md](training-guide.md) | Foundations, twelve modules, and capstone |
| [examples/api.py](examples/api.py) | FastAPI orders service with SQLite persistence |
| [examples/client.py](examples/client.py) | HTTPX command-line client with explicit timeouts and bounded safe retries |
| [examples/test_api.py](examples/test_api.py) | Focused service and client tests |
| [examples/smoke_test.py](examples/smoke_test.py) | Live HTTP checks using temporary orders that it removes afterward |
| [infrastructure/compose.yml](infrastructure/compose.yml) | Local container and persistent data volume |
| [troubleshooting.md](troubleshooting.md) | Symptoms, diagnosis, and recovery |
| [labs/enterprise-extensions.md](labs/enterprise-extensions.md) | Identity, idempotency, gateways, and integration design exercises |
| [VALIDATION.md](VALIDATION.md) | Reproduction commands and actual validation scope |

The compatibility baseline pins FastAPI 0.121.2, Uvicorn 0.38.0, and HTTPX 0.28.1.
These are workshop pins, not a claim that they are the latest releases.

## Safety and architectural boundaries

This is a local HTTP learning environment, not a production template. It binds
host port 8000 to `127.0.0.1`. The explicitly public token `workshop-demo-token`
demonstrates the Bearer header; it is **not a secret or a real identity system**.
Never use it outside this synthetic lab.

There is no TLS, OAuth/OIDC provider, per-user authorization, rate limiter, or
gateway. Swagger UI uses externally hosted frontend assets and may require
internet access. Use only synthetic data. The service uses one SQLite database
and one application worker; horizontal scaling is a design exercise, not a
property demonstrated by this deployment.

The repository's Kafka workshop is independent. REST does not require Kafka,
and this API does not publish Kafka events.
