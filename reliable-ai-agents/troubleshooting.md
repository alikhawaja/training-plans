# Troubleshooting

Run commands from the `reliable-ai-agents` directory. Diagnose the smallest
boundary first; do not increase permissions, disable TLS verification or change
providers to conceal a failure.

| Symptom | Inspect | Recovery |
| --- | --- | --- |
| Compose reports an unset password | `.env` presence and the `--env-file .env` argument | Run `manage.py configure` once. It refuses to overwrite an existing file. Never paste passwords into tracked examples. |
| Port already allocated | `docker compose --env-file .env -f infrastructure\compose.yml ps` and the specific listener | Stop only your known conflicting service, or consistently change the host port and matching `.env` setting. Do not kill processes by name. |
| SQL container fails on ARM | Docker host CPU architecture | Use a supported x86-64 host. Emulation is not a supported SQL Server Linux container configuration. |
| SQL login or database missing | SQL health, `seed-sql` result, reader password | Seed after SQL is ready. Agent tools use `lab_reader`, never `sa`. Changing `.env` does not automatically change passwords in an existing volume. |
| Direct table read or update denied | User and object in the SQL error | Expected for `lab_reader`. Use the approved view through the tool; do not grant administrator or broad reader/writer roles. |
| Zammad initialization still running | `logs --tail 60 zammad-init zammad-railsserver` | Wait for successful initialization, inspect PostgreSQL/search health and available Docker resources. A running container is not necessarily a ready application. |
| Elasticsearch cannot start | Its logs, available memory and Docker VM `vm.max_map_count` | Follow Zammad's official host prerequisite guidance. Any host/kernel change is an operator task, not an agent tool. |
| Zammad 401/403 | API-token access, token expiry, `ticket.agent`, group access | Use a separate Agent user in LabSupport. Do not use the setup administrator token for normal agent runs. |
| Group LabSupport not found | Administration groups | Create the exact group and grant the Agent access before seeding. |
| Ticket rejected by allowlist | `.state\tickets.json` and the intended ticket ID | Use only the explicitly seeded synthetic tickets. Do not widen the tool to all tickets to work around a typo. |
| Interrupted ticket seed | `.state\seed-started.json`, actual Zammad tickets | Inspect the listed IDs and search the UI for all `[ReliableAgentsLab]` tickets. Resolve any timeout ambiguity first. To adopt a complete, verified seed, put exactly its three verified IDs in `.state\tickets.json`; only then remove the specific journal. For a partial seed, finish only missing records manually or use a deliberately fresh lab installation. Do not blindly rerun creation. |
| Tool HTTP connection refused | Host service terminal and `/health` | Start the sample listener at 127.0.0.1:8010. A network error is not an order diagnosis. |
| HTTP 503 | Current controlled scenario | Expected in the unavailable lab. Restore with `manage.py scenario healthy`; recheck rather than assume recovery. |
| Provider/model unset | `AGENT_PROVIDER`, `AGENT_MODEL`, chosen key | Explicitly choose OpenAI or Anthropic. Model IDs are account-dependent; placeholders are not runnable IDs. |
| Provider 401/403, 429 or model unavailable | Provider error and account permissions/usage | Correct access, billing or capacity with that provider. No automatic fallback is configured. Do not loop indefinitely or expose a key in logs. |
| Package download metadata 404 | Configured package index and failing URL | Use an approved working index or verified cached wheel artifacts. This machine's mirror needed a metadata workaround; see VALIDATION.md. Do not disable certificate checks or commit machine-specific index credentials. |
| SDK experimental warning | Pinned adapter/harness feature | Expected for the pinned Microsoft file-memory store and Anthropic adapter status. Review APIs and rerun contracts before upgrades. |
| Budget/no-progress exception | Tool trace, partial report, native limits | Report blocked/partial, identify missing evidence, and involve the operator. Do not simply raise limits until a story sounds complete. |
| Action is submitting/unknown | Exact action record and ticket articles | Use `manage.py reconcile <ID>`. Do not reset status to pending or approve again. No match is not proof that a write will never arrive. |
| Approved note not verified | Article marker, exact body, internal flag | Read back and inspect Zammad. The action remains unresolved until one exact matching article is observed. |
| Model says note posted, but only draft exists | Action ledger and actual ticket | The model is wrong. Drafting never posts. The operator must approve through the separate command. |
| Old Microsoft session behaves unexpectedly | Same run ID used by multiple processes or with changed model/stage | Use single-writer run IDs. Start a new run for incompatible changes. Session JSON is not a crash-durable workflow checkpoint. |
| Qdrant collection missing | Optional service and ingest response | Run optional ingestion first. Do not treat lexical hashing as learned semantic retrieval. |

## Inspect only this project's services

```powershell
docker compose --env-file .env -f infrastructure\compose.yml ps
docker compose --env-file .env -f infrastructure\compose.yml logs --tail 60 sql zammad-init zammad-railsserver zammad-search
```

Logs can contain synthetic ticket data; review before sharing. API keys and
local passwords do not belong in issue reports.

## Persistence and cleanup cautions

`down` preserves named volumes; `down --volumes` destroys this project's database
and application data. This workshop does not use a global prune command.
SQL reseeding resets its three known business rows, not Zammad history.
Use a new run ID rather than recursively deleting state to start a new
conversation. Keep unknown actions until reconciliation has been completed.
