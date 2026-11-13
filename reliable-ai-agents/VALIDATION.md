# Validation and reproduction

## What was exercised

Environment: Windows PowerShell, Python 3.13.17, Docker Engine 29.9.2 with Linux
containers on x86-64. The Docker VM exposed approximately 27.23 GiB RAM. Package
versions are pinned in the track requirements and container tags in Compose.
These are a tested compatibility baseline, not a claim of latest releases.

| Area | Observed result |
| --- | --- |
| Dependencies | Both track requirements installed together; `pip check` reported no broken requirements |
| Compose | Configuration accepted; SQL and web entry points bind to host loopback |
| Required systems | SQL Server, Zammad and its dependencies started successfully; the host Python service responded over a real HTTP listener |
| Business fixtures | Three named synthetic order/payment/shipment records seeded; unknown order returned no record |
| SQL permissions | The reader could read the approved view but was denied base-table reads, updates and table creation |
| Zammad | Restricted Agent account with `ticket.agent` and LabSupport group access created three real tickets; API reads succeeded |
| Approval | Rejection made no write; a separate approved synthetic test note was posted and its article read back successfully |
| Persistence | SQL and Zammad application containers restarted; business data and the approved ticket note remained available |
| Fixed native workflows | Both the LangGraph graph and Microsoft workflow read actual SQL evidence and actual HTTP health |
| Faults | The live listener returned controlled 503 observations, the deterministic loop stopped on repeated unchanged results, and recovery returned healthy |
| Context exercise | Unfiltered logs were bounded to 100 results and reported truncation; order filtering retained the relevant injected-log evidence |
| Deterministic suite | Twelve tests passed, including denial, duplicate drafts, lost-response reconciliation, tool budgets, native graph persistence and provider wire contracts |
| Provider contracts | Both native framework stacks executed tool loops through actual OpenAI/Anthropic adapters using fake HTTP transports; no paid API requests were made |
| Optional retrieval | A real Qdrant server accepted three runbooks; the outage query returned RB-OUTAGE first with its source payload |
| Optional email | A real SMTP message was captured by Mailpit and confirmed through its API |
| Web entry points | Zammad, Qdrant dashboard and Mailpit returned HTML successfully |

An idle snapshot of all required and optional containers totalled roughly
3.1 GiB resident memory. This is **not a minimum requirement or a peak-load
benchmark**: initialization, indexing, the host OS, Python and model activity need
additional resources. Zammad separately documents at least 4 GB for its container
deployment. Budget for SQL Server and the other components in addition.

## Important limits of the evidence

- **No live OpenAI or Anthropic model calls were made.** No provider credentials
  were configured. Fake transport tests establish adapter/schema/tool plumbing,
  not live model availability, diagnosis quality, refusal behavior or costs.
- The pinned Microsoft Anthropic adapter is a prerelease; the file-memory
  implementation emits an experimental-feature warning. Recheck contracts on
  upgrade.
- The actual Zammad validation setup used its local operator console to create
  the initial synthetic administrator, then its HTTP API to create the restricted
  group/user/token. The student-facing initial browser setup is documented but
  was not automated end to end.
- Web HTML was checked, but no browser-driven visual UI or approval-click test
  was performed. Students verify the real records in the UI as part of the labs.
- Streaming and model-selected specialist delegation have not been exercised
  against a live provider. All stage factories were constructed without model
  requests. Do not equate configuration with successful semantic delegation.
- Microsoft session serialization is not a crash-durable workflow checkpoint.
  The guide explicitly distinguishes that from LangGraph's durable checkpointer.
- Qdrant uses explicit lexical hashing here, **not learned semantic embeddings**.
  An additional embedding-service integration is a learner extension, not a
  tested shipped provider feature.
- The fulfillment outage is an operator-controlled local diagnostic fault, not
  a claim of an actual production carrier or payment outage.
- This is not a production security, performance or multi-host assessment.
  Prompt-injection exercises do not prove semantic immunity.
- ARM hosts, other Python versions, and non-Windows host command adaptations
  were not executed here.

## Reproduce the smallest checks

From `reliable-ai-agents`, install either track as described in the guide.
Installing both is only necessary to run every native contract test:

```powershell
.\.venv\Scripts\python.exe -m pip install -r examples\requirements-langchain.txt -r examples\requirements-microsoft.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s examples -p "test_*.py" -v
docker compose --env-file .env -f infrastructure\compose.yml config --quiet
```

Tests for a track not installed are skipped. The domain/approval tests remain
independent of paid model calls. Fake provider transports use non-secret test
keys and never contact model services.

For real-system checks, start the stack and listener, complete Zammad setup and
seed both databases according to the guide:

```powershell
.\.venv\Scripts\python.exe examples\manage.py seed-sql
.\.venv\Scripts\python.exe examples\manage.py seed-tickets
.\.venv\Scripts\python.exe examples\smoke_test.py -v
.\.venv\Scripts\python.exe examples\workflow.py --track langchain ORD-1001
.\.venv\Scripts\python.exe examples\workflow.py --track microsoft ORD-1001
```

The smoke check deliberately creates a **local pending draft**, not a ticket
write. For an actual approved write, follow module 11 and inspect the resulting
article ID. Lost-response reconciliation is deterministic in `test_workshop.py`;
the real server was not deliberately made to lose a committed write response.

Use the optional lab instructions to reproduce Qdrant and Mailpit checks.
Model-quality evaluation requires an explicitly selected accessible model and
credential, the `--allow-model-calls` flag, and the behavioral rubric in module 13.

## Package-index limitation on this machine

The configured package mirror advertised a wheel metadata URL that returned 404.
Direct public-index installation then failed during TLS negotiation with
`files.pythonhosted.org`. Certificate verification was **not disabled**.

Installation succeeded using the configured mirror's wheel artifacts with pip's
legacy resolver, followed by explicit compatible transitive pins and a successful
`pip check`. This is a local workaround, not a recommended replacement for a
working dependency resolver. The normal published commands use standard pip;
repair your approved index/network path if the same issue occurs.

## Cleanup

The validation services and their task-owned disposable volumes are removed after
the checks. Python dependencies remain in the ignored workshop virtual environment.
No live model keys, ticket tokens, passwords or runtime databases are included in
the source changes. The guide's normal `down` command preserves student data;
destructive volume deletion is separately identified.
