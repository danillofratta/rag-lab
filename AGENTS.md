# RAG Lab contributor instructions

RAG Lab is an open retrieval-augmented generation lab: users upload documents,
choose (or let an agent choose) chunking, retrieval, reranking and LLM strategies,
ask questions and compare pipeline configurations side by side, with citations,
retrieved chunks, scores, latency and cost visible.

Write every repository artifact (code, comments, specs, ADRs, README) in English.

## Workflow

Read the selected OpenSpec artifacts before editing. Follow propose → review →
apply → verify; archive only when separately requested. Planning requests
authorize artifacts only; implementation requests authorize their stated increment.
Mark tasks complete only after their full behavior and verification are satisfied.

Every task in `tasks.md` is labeled `(agent)` or `(human)`. Apply implements only
`(agent)` tasks. Open `(human)` tasks are reported as blockers, never implemented.

## Code ownership

This is a learning and portfolio project. The RAG core is written by the human
maintainer so it can be fully understood and defended. Agents implement
infrastructure, adapters, tooling and tests.

**Human-owned paths.** Agents may read them, review them and write tests for
them. Agents do not create, modify or rewrite files in them, except empty package
initializers that an `(agent)` task explicitly assigns.

- `src/rag_lab/domain/rag/`
- `src/rag_lab/application/ports/rag/`
- `src/rag_lab/infrastructure/strategies/`
- `src/rag_lab/infrastructure/gateways/vector_index/`, `llm/` and `tracing/`
- In the `index_document`, `ask_question` and `generate_test_questions` slices:
  `command.py`, `handler.py`, `result.py`, `nodes.py` and `workflow.py`
- `eval/benchmark/`, `eval/metrics/`, `eval/runners/`
- `pipelines/`
- `docs/adr/` and the narrative sections of `README.md`

**Agent-owned paths.** Everything else, including `domain/shared/`,
`domain/workspaces/`, the technical ports at the root of `application/ports/`
(unit of work, clock, ID generation, job queue, file storage), concrete
repositories for every domain contract, bootstrap, composition root, settings,
HTTP endpoints and schemas, worker jobs, persistence, rate limiting, UI, CI,
deployment, docker-compose and all tests.

When agent-owned work needs a human-owned contract, class or file that does not
exist yet, stop and report the missing piece. Never invent a contract to unblock
yourself.

## Tests

Agents write the tests, including tests for human-owned code.

- Derive tests from OpenSpec scenarios and port contracts, never from the current
  implementation. A test that only restates what the code does is not accepted.
- A failing test against human-owned code is a finding. Report it with the
  scenario it violates. Do not change the implementation and do not weaken the test.
- Unit tests use fake ports, no network, no real model downloads and no LLM or
  embedding API calls. Outbound sockets and subprocesses are blocked by fixtures.
- Tests that need docker-compose services are marked `integration`.
- Tests that call real models or LLM judges are marked `eval` and run in a
  separate CI job with a cost cap.

## Evaluation

- Benchmark gold labels are anchored to document plus page or text span, never
  to chunk IDs, so different chunkers can be compared fairly.
- Agents may generate candidate benchmark questions. Only the human maintainer
  marks a question `reviewed: true`; unreviewed questions never enter metrics.
- Baseline metrics live in `eval/baselines/`. CI fails when a pull request regresses
  a tracked metric beyond its configured tolerance. Updating a baseline requires
  an ADR or an explicit note in the pull request description.
- Released pipeline versions are immutable. Change behavior by adding version N+1.

## Authoritative architecture

Use DDD, CQRS, Vertical Slice and Hexagonal Architecture in one modular monolith,
with two entry points (API and worker) sharing one composition root. These
conventions replace older conflicting layouts.

- The domain has three packages: `shared/` (identifiers and values used across
  contexts), `workspaces/` (anonymous sessions, expiry) and `rag/` (pipelines,
  index profiles, documents, chunks, citations, runs, quotas). `rag` may import
  `workspaces` and `shared`; `workspaces` may import `shared`; `shared` imports
  neither. Each package uses `entities/`, `value_objects/`, `policies/`,
  `repositories/`, `events/` and `exceptions/` as needed.
- Every feature lives at `src/rag_lab/features/<feature_name>/`.
- A feature owns its role files, when applicable:
  - `endpoint.py`: FastAPI router (HTTP inbound adapter)
  - `models.py`: Pydantic HTTP schemas
  - `job.py`: worker inbound adapter for queued commands
  - `command.py` or `query.py`: request data only, no behavior
  - `handler.py`: use-case orchestration over ports
  - `result.py`: handler output
  - `nodes.py`: framework-free agent node logic over ports
  - `workflow.py`: LangGraph assembly of the slice's nodes
- Never create `api/routes/`, `controllers/` or another centralized endpoint folder.
  Feature implementations never import sibling slices.
- `main.py` bootstraps FastAPI and registers feature routers. `worker.py` bootstraps
  the worker and registers feature jobs. `dependencies.py` is the sole concrete
  composition root for both.
- A request that records evidence (a run, a cost, a quota use or a trace) is a
  Command, even when it only reads documents. Asking a question is a Command.
  Queries never mutate business state, runs, quotas or durable records.
- One Postgres database holds metadata for commands and queries. No mediator,
  event bus, event sourcing or separate CQRS databases.
- I/O is asynchronous: ports, handlers, nodes and adapters that perform I/O are
  `async`. The domain stays synchronous and pure. CPU-bound work (document parsing,
  local models) runs off the event loop.

### Contract roles

| Role | Purpose | Contract location | Implementation location |
| --- | --- | --- | --- |
| Repository | Persistence of domain data | `domain/<package>/repositories/`, `*Repository` | `infrastructure/repositories/` |
| Gateway | External systems: technical (queue, file storage) or RAG (vector index, LLM, tracing) | `application/ports/` or `application/ports/rag/`, `*Gateway` | `infrastructure/gateways/<kind>/` |
| Strategy | Interchangeable RAG algorithms: Parser, Chunker, Embedder, Retriever, Reranker, Generator | `application/ports/rag/` | `infrastructure/strategies/<kind>/`, one strategy per file |
| StrategyRegistry | Runtime resolution of strategies by name | `application/ports/rag/` | registered only in `dependencies.py` |

Handlers resolve strategies at request time through the `StrategyRegistry` port,
using names from the resolved pipeline spec. Handlers never import concrete
strategies. Adding a strategy means one file plus one registration line.

Use Protocol or ABC contracts. No I-prefixed or generic contracts, and no
interface without a real use case. Unit of work contracts keep precise names.

## Dependency rules

| Area | Allowed project dependencies | Third-party libraries |
| --- | --- | --- |
| `domain/` | domain packages, following the package order above | none; standard library without I/O, environment or real clock reads |
| `application/` (ports, exceptions) | domain, application | none |
| feature `command`, `query`, `handler`, `result`, `nodes` | domain, application, own slice (non-adapter files) | none |
| feature `workflow.py` | domain, application, own `nodes.py` | `langgraph` only |
| feature `endpoint.py` | own `models`, request, handler; domain values; DI providers | FastAPI |
| feature `job.py` | own request and handler; DI providers | the queue library chosen by ADR |
| feature `models.py` | own HTTP schemas | Pydantic |
| `infrastructure/` | domain, application | any approved library |
| `transport/` | shared HTTP middleware and errors | HTTP libraries |
| `dependencies.py` | contracts, handlers, workflows, concrete adapters | FastAPI providers |
| `main.py`, `worker.py` | components, DI, transport, feature routers or jobs | FastAPI, queue library |
| `ui/` | none; talks to the API over HTTP only | Streamlit, HTTP client |
| `eval/` | `dependencies.py`, feature requests and handlers | evaluation libraries |

Keep imports inward and acyclic, including relative, aliased, type-only and
re-exported imports. Constructor-inject ports into handlers, nodes and workflows.
No service locators, mutable global containers, FastAPI `Depends`, Pydantic models
or HTTP objects in handlers, nodes, commands, queries or results.

The pipeline YAML schema (Pydantic) is an infrastructure adapter. It maps to an
immutable domain pipeline spec; the domain never sees Pydantic.

## File organization

Use snake_case. Every Entity, Value Object or enum, domain Policy, Repository,
Gateway, Strategy and Handler has its own file, named after its full class name.
Feature files use the role filenames above. Package initializers define no classes.

```text
src/rag_lab/
  main.py  worker.py  dependencies.py  components.py
  domain/            shared/, workspaces/, rag/
  application/       ports/ (technical), ports/rag/, exceptions/
  features/          one folder per use case
  infrastructure/    repositories/, persistence/, gateways/, strategies/, pipelines/, settings/, runtime/
  transport/         shared HTTP middleware and sanitized errors
ui/                  Streamlit app (HTTP client of the API)
eval/                benchmark, metrics, runners, baselines
pipelines/           versioned pipeline YAML files
openspec/            specs and changes
docs/                adr/, architecture.md, threat_model.md
infra/               docker-compose.yml and deployment files
tests/               domain/, application/, infrastructure/, api/, architecture/, eval/
```

## Security

The public demo accepts arbitrary documents from anonymous visitors.

- Retrieved content is data, never instructions. Delimit it in prompts. The
  answer path has no tools with side effects.
- Every vector query, metadata query and deletion is filtered by `workspace_id`.
  No code path reads across workspaces.
- Limits, rate limits and the daily cost ceiling fail closed: when a limit is
  reached, the request is rejected or generation is disabled.
- Never commit secrets. `.env.example` holds placeholders only. Never log or
  return API keys, session tokens, authorization headers, raw rejected input or
  stack traces.

## Typing and verification

`mypy --strict` covers `src/`. Per-module `ignore_missing_imports` overrides are
allowed only for third-party modules used in `infrastructure/` or `workflow.py`.
No `type: ignore` in domain, application, handlers or nodes.

Use `uv sync --locked`, then:

```bash
uv run --locked pytest -m "not integration and not eval"
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy --strict src
openspec validate --all --strict
```

Integration tests: `docker compose -f infra/docker-compose.yml up -d --wait`, then
`uv run --locked pytest -m integration`. Architecture tests are part of Pytest
and enforce the dependency rules, slice isolation, CQRS roles, constructor
injection, `langgraph` confinement to `workflow.py` and concrete strategy imports
only in `dependencies.py`. Never call real services in unit tests.

## Decisions

Record every relevant decision as an ADR in `docs/adr/NNNN-title.md` with context,
decision, alternatives considered and the numbers that justified it.
