# Training plans

Self-paced training for developers and technical teams, progressing from
diagram-led foundations to working applications, failure recovery, and enterprise
architecture decisions. Each plan combines guided explanations, runnable examples,
knowledge checks, and a capstone.

| Training | Focus | Audience | Start here |
| --- | --- | --- | --- |
| Apache Kafka | Event streaming, producers and consumers, partitions, replay, and resilience | Basic programming and terminal familiarity; no enterprise-system background required | [Kafka workshop](kafka/README.md) |
| REST APIs | Clients and servers, HTTP, resource design, validation, authentication, and reliable requests | Basic Python and terminal familiarity; no web or enterprise-system background required | [REST API workshop](rest-apis/README.md) |
| LangChain Deep Agents | Agent foundations, tools, loop engineering, planning, context, delegation, and human approval | Basic Python familiarity; no prior agent-framework experience required | Planned; guide not yet published |

## What each training prepares you for

### Apache Kafka

**Scope:** Twelve modules cover event-streaming foundations, container setup,
Python producers and consumers, keys and partitions, consumer groups, offsets and
replay, delivery guarantees, deduplication, dead-letter handling, retention,
compaction, replication, and broker failure. A Kafka Connect exercise and enterprise
integration discussions extend the core application.

**You will be able to:** Build and troubleshoot event-driven applications, choose
partition keys and consumer-group boundaries, recover processing through replay,
handle duplicate and invalid events, and explain availability and durability
tradeoffs. The capstone brings these skills together in an order-processing system
with independent fulfillment and analytics consumers.

**Cost and resources:** The core exercises run locally with Apache Kafka and
Python, without a paid Kafka service or cloud account. Budget approximately 4 GB
of available container memory for the single broker, 8 GB for the three-broker
exercises, and 10 GB of free disk space. Docker licensing depends on your
organization's usage and subscription terms.

### REST APIs

**Scope:** Twelve modules progress from clients, servers, HTTP, and REST to a
Python API and client. Exercises cover CRUD, resource contracts, OpenAPI,
validation and structured errors, authentication, filtering and pagination,
caching, ETags, concurrent updates, timeouts, retries, and request observability.

**You will be able to:** Build and consume resource-oriented HTTP APIs, interpret
requests and responses, design predictable contracts, prevent stale updates,
handle failures explicitly, and diagnose interactions across client and server.
The capstone combines multiple clients, persistent orders, conditional requests,
failure recovery, and request-log correlation. Enterprise exercises develop
decisions around identity, gateways, compatibility, and integration.

**Cost and resources:** The core exercises use local Python applications and
SQLite, with an optional Docker server path and no cloud-service charges.
Allow about 2 GB of free disk space and approximately 1 GB of available container
memory when using Docker. Docker licensing depends on your organization's terms.

### LangChain Deep Agents

**Proposed scope:** A foundations-first progression through models, tools, agent
loops, and the LangChain ecosystem, followed by planning, filesystem context,
subagents, persistence, human approval, observability, and evaluation. Loop
engineering covers completion criteria, progress detection, bounded retries,
execution budgets, and stopping behavior.

**Intended preparation:** Build and assess multi-step assistants that gather
evidence, use controlled tools, delegate bounded tasks, recover from failures,
and request approval for consequential actions. The proposed capstone is a
technical-support investigation assistant that produces evidence-backed findings
and identifies unresolved questions.

**Expected cost drivers:** Live exercises will require a tool-capable model.
Provider charges depend on the selected model, token usage, tool calls, repeated
runs, and subagent activity. Provider choice and spending guidance will be
specified with the implementation; optional search, tracing, or hosting services
may add charges. A local-model path would require suitable hardware and verified
tool-calling support.

## Authoring and updating training

Use the repository's [training-plan-builder skill](.github/skills/training-plan-builder/SKILL.md)
to create or align modules. It includes a [module template](.github/skills/training-plan-builder/templates/module.md),
a [training overview template](.github/skills/training-plan-builder/templates/training-overview.md),
and a [review checklist](.github/skills/training-plan-builder/references/review-checklist.md).
The shared format connects explanations, guided labs, independent exercises,
failure checks, and evidence, with explicit prerequisites and module handoffs.

[REST module 3](rest-apis/modules/03-create-and-read/README.md) is the initial pilot;
the other modules have not yet been migrated.
