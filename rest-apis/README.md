# REST APIs: from a request to an enterprise service

Learn what an API is before building one. Begin with a gentle, diagram-led
introduction to clients, servers, HTTP, and REST, then build and use an order API.

**Start with the [training guide](training-guide.md).** It includes explanations,
commands, expected responses, failure exercises, and a capstone.

**Module-format pilot:** [Module 3: Create an order and read it back](modules/03-create-and-read/README.md)
adds a separate guided lab, independent coding exercise, failure checks, evidence
criteria, and a reference solution. Start with the guide's foundations and setup
before that module; the remaining modules retain their existing format.

## Prerequisites

- Basic Python and terminal familiarity; no web or enterprise-system background.
- Python 3.11-3.13 for the host examples; the container uses Python 3.13.
- Docker with Linux containers and Docker Compose v2.20 or newer.
- Internet access for the image and Python packages, about 2 GB free disk space,
  and approximately 1 GB available container memory for this small local service.
- Available loopback port 8000 and a browser. No cloud account is required.

Commands are written for Windows PowerShell, with macOS/Linux adaptations.
The API and client can also run without Docker, as described in the guide.

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
| [modules/03-create-and-read](modules/03-create-and-read/README.md) | Canonical module 3 lesson and guided/independent activities |
| [exercises/03-create-and-read.py](exercises/03-create-and-read.py) | Learner starter for the module 3 client |
| [solutions/03-create-and-read.py](solutions/03-create-and-read.py) | Completed example to review after attempting the exercise |
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
