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

### Cross-platform documentation revision

The revised instructions were checked on Windows with PowerShell 7.7 and host
Python 3.13. The documented venv setup and dependency installation succeeded;
all nine service/client tests passed again.

All seven shared Python blocks from the guide were exercised in order using
Python's interactive-console semantics against a temporary native Uvicorn server.
The checks confirmed list/read, PATCH/PUT, filtered multi-page traversal, a
bodyless 304, a stale-write 412, and deletion followed by 404. The CLI exercises,
authentication/validation failures, docs/OpenAPI responses, and live smoke check
also passed. The temporary server and its isolated database were removed.

The PowerShell fenced blocks parsed successfully, and the bash/zsh blocks passed
`bash -n` syntax checks using Git Bash on Windows. Relative file links and Compose
configuration were checked. These checks do **not** establish native macOS/Linux
or zsh execution, Windows PowerShell 5.1 execution, installer success on each OS,
or a successful standard online Docker build.

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

**Windows - PowerShell:**

```powershell
.\.venv\Scripts\python.exe -m pip install -r rest-apis\examples\requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s rest-apis\examples -p test_api.py -v
```

**macOS/Linux - bash or zsh:**

```bash
.venv/bin/python -m pip install -r rest-apis/examples/requirements.txt
.venv/bin/python -m unittest discover -s rest-apis/examples -p test_api.py -v
```

For a **Docker server**, start it, run the live smoke check, and stop it while
retaining its volume:

**Windows - PowerShell:**

```powershell
docker compose -f rest-apis\infrastructure\compose.yml config --quiet
docker compose -f rest-apis\infrastructure\compose.yml up -d --build --wait --wait-timeout 120
.\.venv\Scripts\python.exe rest-apis\examples\smoke_test.py
docker compose -f rest-apis\infrastructure\compose.yml down
```

**macOS/Linux - bash or zsh:**

```bash
docker compose -f rest-apis/infrastructure/compose.yml config --quiet
docker compose -f rest-apis/infrastructure/compose.yml up -d --build --wait --wait-timeout 120
.venv/bin/python rest-apis/examples/smoke_test.py
docker compose -f rest-apis/infrastructure/compose.yml down
```

For a **native server**, skip Docker completely. Start Uvicorn using your
platform's command in module 2, run only the smoke command for your platform
above in a second terminal, then stop Uvicorn with Ctrl+C.

Tests use temporary databases and do not need a live API. The smoke check instead
calls the real listener, creates uniquely referenced orders, and deletes only
the orders whose resource addresses it recorded. A failure during creation before
the response arrives may require manual reconciliation, just like any ambiguous
write. Smoke cleanup errors are surfaced, not silently ignored.

## Boundaries

- Complete bash/zsh shell instructions and shared Python/HTTPX exercises are
  provided for macOS/Linux; native macOS/Linux execution is not claimed.
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
