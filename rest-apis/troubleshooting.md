# REST API workshop troubleshooting

Run commands from the repository root using the variables in the
[training guide](training-guide.md#environment-preparation).
Inspect errors before resetting data.

## Container build or installation fails

```powershell
docker info
docker compose -f $Compose config --quiet
docker compose --progress plain -f $Compose build
```

Start Docker Desktop/Engine and use Linux containers. Check free disk, approved
proxy configuration, and access to Docker Hub, PyPI, and its package-file host.
Container networking and certificate stores can differ from the host.

For TLS handshake or certificate errors, use your organization's approved
network/proxy/CA configuration. Do not disable certificate checks or switch to
an untrusted package index. If the host can install dependencies, the documented
host-mode server remains an alternative for learning while container networking
is repaired; it uses separate storage.

## Port 8000 is already in use

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

Do not terminate unrelated processes. Stop only your own previous workshop
listener. If changing the published host port, update the client's `--base-url`,
browser address, and `$Base`. The internal container port and health check remain 8000.

## Connection refused or client retries

```powershell
docker compose -f $Compose ps -a
docker compose -f $Compose logs --tail 50 api
& $Python rest-apis\examples\client.py health
```

Verify the server is listening, healthy, and at the selected address.
`127.0.0.1` inside another container is not the host or this API container.
Another service on the Compose network would use `http://api:8000`, but no such
service is deployed in this workshop.

Read retries are bounded. Persistent failure returns nonzero, not an empty
collection. A timed-out write may already have completed; reconcile its outcome.

## Swagger UI is blank or cannot load assets

The docs HTML can load while its CDN-hosted JavaScript or stylesheet is blocked.
Use approved network settings, inspect `/openapi.json`, or use the Python client.
A successful docs page is not proof that protected endpoints accept your credentials.

## 401 Unauthorized

Select Authorize in Swagger UI and enter only `workshop-demo-token`; the UI adds
`Bearer`. The CLI uses this public demo value by default. If you deliberately
change server configuration, configure the client consistently.
An HTTP 401 is a server response, unlike a connection failure.

## 404 versus 422

A syntactically valid but nonexistent order UUID returns 404. A malformed UUID
returns 422. A missing route returns 404. Replace guide placeholders with actual
IDs from your create responses, not sample strings.

## 409 Conflict on create

References are unique in this learning API. Use a fresh `--reference` or omit it
for an automatically generated value. A duplicate reference is not an idempotency
response cache: the service does not replay the original 201 response.

## 422 validation failure

Inspect the Problem Details `errors` array. Quantity must be an integer from
1 to 100; item must be a nonempty trimmed string up to 80 characters. Unknown
fields are rejected. PUT requires item, quantity, and status. PATCH requires at
least one supported field and does not accept explicit null.
Inspect the OpenAPI schemas rather than guessing field types.

## 428 or 412 on update/delete

Read the order and copy its ETag, including quotes, into `If-Match`.
Missing headers cause 428; an outdated version causes 412.
Re-read and reconcile if someone else changed the order. The PowerShell header
dictionary avoids shell quoting problems with quoted ETags.
`If-Match: *` only checks existence and is not a version-conflict solution.

## 304 or 204 has no JSON body

That is intentional. A 304 means reuse the cached representation; the demo client
does not maintain one for you. A 204 deletion has no representation. Do not
decode an empty response as JSON.

## Browser frontend fails while Python works

Inspect origin and browser CORS messages. CORS applies to browser scripts, not
Python/curl, and is not an identity control. The supplied Swagger UI shares the
API's origin. A separate frontend needs deliberately configured allowed origins.

## Data seems missing or persists unexpectedly

The container uses a named volume; `down` keeps it and `down --volumes` deletes it.
Host Uvicorn uses `.state/rest-api.db`, a different database. Restart the same mode
before comparing records. Repeated labs accumulate orders; exact totals depend on
your earlier actions. Do not reset unrelated Kafka volumes or databases.

## Database errors or 503

Inspect the server's request-ID-tagged error log. Check free space, write permissions,
and contention. The container runs as a non-root user and expects its managed
`/data` volume to be writable. A custom bind mount needs compatible permissions.

SQLite is appropriate for this small local exercise, not proof of multi-instance
production scalability. Do not hide operational errors with fake success or
retry every failed write indiscriminately.

## Tests or imports fail

```powershell
.\.venv\Scripts\python.exe -m pip install -r rest-apis\examples\requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s rest-apis\examples -p test_api.py -v
```

Use the same Python environment for installation and execution. If running the
host server, include the documented `--app-dir rest-apis\examples`. The tests use
temporary SQLite files and do not require a live container or the Kafka packages.
