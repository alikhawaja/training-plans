# Validation and reproduction

## Recorded scope

The initial workshop was exercised on **2026-11-13** using Windows PowerShell,
host Python 3.13, Docker Desktop Linux containers, and the compatibility pins in
`examples/requirements.txt`. The container runtime was Python 3.13.9.

| Area | Observed result |
| --- | --- |
| Compose configuration | Accepted; client port is bound to host loopback |
| Container runtime | Started healthy as non-root with a writable persistent data volume |
| Live HTTP smoke check | Create, read, replace, patch, delete, validation, authentication, uniqueness, paging, conditional read, and stale-write handling passed |
| CLI | Real create/list/get calls printed statuses and headers; an HTTP 401 exited nonzero |
| PowerShell examples | Header dictionaries preserved quoted ETags; PATCH and PUT succeeded; stale writes returned 412 |
| Conditional read | The CLI received a bodyless 304 using the server-returned ETag |
| curl and documentation | A real list call succeeded; docs HTML and OpenAPI were served |
| OpenAPI | Bearer authentication and Problem Details validation media type match the implementation |
| Persistence | A created order survived container removal/recreation without deleting its volume |
| Logs | Response request IDs matched application log entries |
| Live outage | Stopping the API caused bounded read retries and a nonzero client exit; restarting restored service |
| Focused tests | Nine service/client tests passed, including validation, conflicts, paging, ETags, persistence, retry budgets, and ambiguous write failures |

### Container build limitation

The standard online Docker build failed in this environment while negotiating
TLS with `files.pythonhosted.org` for a package download. Host-side pip downloads
worked. Certificate verification was **not** disabled.

For runtime verification, Linux wheels were downloaded from the configured PyPI
index using the host's working TLS connection. A temporary offline build used
the same base image, application source, dependency requirements, non-root user,
data path, and Uvicorn command. The only build-path difference was installing
those wheels with `--no-index --find-links` instead of downloading them inside
Docker. Temporary build inputs are not part of this workshop.

Thus container application behavior was verified, but a successful online build
from the published Dockerfile on this machine is **not** claimed. The normal
Dockerfile remains an online installation for environments with working PyPI
access. Repair approved container network/proxy configuration or use the
documented host-mode server if you encounter the same issue.

## Reproduce the smallest checks

From the repository root, using an existing virtual environment or creating one
as described in the guide:

```powershell
.\.venv\Scripts\python.exe -m pip install -r rest-apis\examples\requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s rest-apis\examples -p test_api.py -v
docker compose -f rest-apis\infrastructure\compose.yml config --quiet
docker compose -f rest-apis\infrastructure\compose.yml up -d --build --wait --wait-timeout 120
.\.venv\Scripts\python.exe rest-apis\examples\smoke_test.py
docker compose -f rest-apis\infrastructure\compose.yml down
```

Tests use temporary databases and do not need a live API. The smoke check instead
calls the real listener, creates uniquely referenced orders, and deletes only
the orders whose resource addresses it recorded. A failure during creation before
the response arrives may require manual reconciliation, just like any ambiguous
write. Smoke cleanup errors are surfaced, not silently ignored.

## Boundaries

- macOS/Linux host command adaptations are provided but were not executed there.
- Swagger HTML and OpenAPI were checked; CDN asset loading and an interactive
  browser session were not automated.
- OAuth/OIDC, user-level authorization, HTTPS, CORS for a separate frontend,
  rate limiting, gateways, distributed tracing, and Kafka integration are
  explanations/design exercises, not deployed features.
- Client retries for 429/503 and transport ambiguity are tested with a deterministic
  mock transport; the service does not install a real rate limiter.
- No production load, multi-host failover, penetration test, or complete
  hypermedia-REST conformance is claimed.

The validation container, its generated data volume, and temporary offline build
inputs were removed after the checks. The host virtual environment remains
available and is excluded from version control.

## Module 3 format pilot

The standalone [module 3](modules/03-create-and-read/README.md) was exercised
using Windows PowerShell, host Python 3.13.17, and HTTPX 0.28.1. The existing
FastAPI application ran against a separate temporary SQLite database and
loopback port 18063 to avoid changing learners' database or occupying their
normal port 8000. CLI launches used `--base-url http://127.0.0.1:18063`;
the published lesson keeps the normal port 8000.

| Area | Observed result |
| --- | --- |
| Guided create/read/list | CLI create returned 201, quantity 2, pending status, and Location matching the returned ID; direct GET returned the same complete representation; list succeeded |
| Repeated GET | Same business data and ETag, with no created order |
| Reference exercise | Created and followed Location, rejected a duplicate with 409/Problem Details, and confirmed the original representation was unchanged |
| Repeat runs | Default references differed; rerunning with an already used reference failed explicitly rather than reporting success |
| Unauthorized run | Wrong token failed with 401 and a nonzero process exit; no resource was created |
| Learner starter | Deliberately failed with NotImplementedError before making requests |
| State and handoff | Separate guided order remained unchanged; exactly three orders were present in the isolated database after one guided create and two successful exercise runs |
| Existing service/client tests | All nine passed unchanged |
| Reference solution tests | Three passed: follows Location, stops on unexpected create status, and rejects changed final state |
| Shared format checker | Module passed structural checks; four checker tests passed, including incomplete structure, placeholders, missing links, durations, and unclosed fences |

Reproduce the non-live checks from the repository root:

```powershell
.\.venv\Scripts\python.exe .github\skills\training-plan-builder\scripts\check_module.py rest-apis\modules\03-create-and-read\README.md
.\.venv\Scripts\python.exe -m unittest discover -s .github\skills\training-plan-builder\scripts -p test_check_module.py -v
.\.venv\Scripts\python.exe -m unittest discover -s rest-apis\solutions -p test_create_and_read.py -v
.\.venv\Scripts\python.exe -m unittest discover -s rest-apis\examples -p test_api.py -v
```

For a live repeat, start the module 2 server and run the reference exercise:

```powershell
.\.venv\Scripts\python.exe rest-apis\solutions\03-create-and-read.py
```

That command leaves its order available for inspection, as the lesson explains;
it does not delete shared data. The pilot verification server was stopped and
its isolated database removed afterward.

macOS/Linux launch commands are supplied but were not executed on those hosts.
The module's Mermaid source was reviewed, not rendered in an automated browser.
Swagger HTML and OpenAPI were served successfully; no interactive Swagger session
or new Docker build was part of this pilot. The exercise starter remains a learner
task, not a pre-completed implementation. Other modules are not claimed to conform
to the new format yet.
