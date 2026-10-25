# Design

## Context

The repository is new. `AGENTS.md` is the authoritative architecture and ownership contract; this design explains how the foundation satisfies it. The reference implementation for the development harness is AgentGate (`github.com/danillofratta/agentgate-sdd`), which already enforces DDD, CQRS, Vertical Slice and Hexagonal rules through AST architecture tests. RAG Lab reuses that harness and adapts it to two entry points, runtime strategy selection, an agent framework and asynchronous I/O. See proposal.md for motivation and the four capability specs for behavior.

## Goals / Non-Goals

**Goals:**
- A harness strict enough that agent-written code cannot silently break architecture rules.
- A running API with persistence and workspace sessions, so the next change can add document upload and questions without touching plumbing.
- Empty, correctly placed packages for every human-owned area.

**Non-Goals:**
- Any RAG behavior: parsing, chunking, embeddings, vector indexing, retrieval, reranking, generation, agents or evaluation.
- The worker process and queue technology (a later ADR decides; ingestion starts in-process behind a port in the next change).
- Rate limits, workspace cleanup, UI, deployment and the evaluation CI job.

## Decisions

### 1. Toolchain

Python 3.12, uv with a committed lock file, hatchling with a `src/rag_lab` layout, Ruff for lint and format, mypy in strict mode, pytest with the AnyIO plugin for async tests and HTTPX for in-process API tests. Network and subprocess blocking fixtures follow AgentGate. Markers `integration` and `eval` are registered and excluded by default.

*Alternatives:* Poetry (slower resolver, not used in AgentGate); pytest-asyncio (extra dependency, while AnyIO already ships with the web stack).

### 2. Architecture tests ported from AgentGate

Copy `tests/architecture/` (`rules.py`, `test_boundaries.py`, `test_cqrs.py`, `test_dependency_injection.py`) and make the root package name a single constant. Keep every existing positive and negative fixture, then add rules for:

| Rule | Allowed | Rejected |
| --- | --- | --- |
| Domain package order | `rag` → `workspaces` → `shared` | `workspaces` or `shared` importing `rag`; `shared` importing `workspaces` |
| Feature role files | `endpoint`, `models`, `job`, `command`/`query`, `handler`, `result`, `nodes`, `workflow` | other module names in a feature, mixed command and query |
| Agent framework | `langgraph` in `features/*/workflow.py` | anywhere else, including infrastructure |
| Validation models | Pydantic in `features/*/models.py` and `infrastructure/` | handlers, nodes, requests, results, domain, application |
| Composition | concrete repositories, gateways and strategies constructed in `dependencies.py` | construction in handlers, nodes, workflows, endpoints, jobs |
| UI isolation | `ui/` imports only third-party and standard-library modules | any `rag_lab` import |
| Evaluation entry | `eval/` imports `rag_lab.dependencies` and feature requests and handlers | infrastructure or domain internals |

AST checks are regression gates against accidental violations, not a sandbox.

### 3. Asynchronous I/O

Endpoints, handlers, nodes, ports and adapters that perform I/O are `async`; the domain stays synchronous and pure. Question answering waits on vector search, reranking and LLM calls, and pipeline comparison runs up to three pipelines concurrently; the planned libraries for those steps offer async APIs. CPU-bound work such as document parsing will run off the event loop when it arrives.

*Alternative:* synchronous handlers as in AgentGate. Simpler, but each LLM call would hold a worker thread and concurrent comparison would need thread management. This decision is recorded by the maintainer as ADR 0002.

### 4. Persistence

Postgres through the psycopg 3 async driver with a connection pool and parameterized SQL, no ORM. A unit of work owns one connection and one transaction; repositories receive that connection and map rows to domain objects. Repository contracts live in `domain/<package>/repositories/`; implementations live in `infrastructure/repositories/`.

Migrations are numbered SQL files in `infrastructure/persistence/migrations/` applied by an explicit command (`python -m rag_lab.infrastructure.persistence.migrate`). Applied versions are recorded with a checksum; a changed checksum fails the command. The API never migrates automatically; readiness reports the database as not ready when the recorded version differs from the latest file.

*Alternatives:* SQLAlchemy with Alembic (heavier, encourages ORM entities that compete with the domain model); auto-migration on startup (unsafe with several replicas and hides schema changes from review).

### 5. Settings and composition

Typed settings with the `RAG_LAB_` prefix live in `infrastructure/settings/`, with secrets typed so they never render in logs or errors. `dependencies.py` builds a typed `components.py` bundle inside the API lifespan (settings, pool, clock, generators, repositories factories, handlers) and closes the pool on shutdown. FastAPI providers exist only in `dependencies.py` and endpoints.

### 6. Transport

Shared middleware in `transport/`: request ID (accept a well-formed incoming `X-Request-ID`, otherwise generate one), body limit enforced on streamed bytes, exception mapping to the error envelope, and JSON logging through the standard library with a filter that drops authorization headers and bodies. Liveness and readiness are a query feature slice (`check_health`) using a technical `HealthProbe` port implemented in infrastructure, so health follows the same slice rules as everything else.

### 7. Workspace sessions

- Domain (`domain/shared`, `domain/workspaces`): `WorkspaceId`, `SessionTokenHash`, the `Workspace` entity with `is_expired(now)` (expired when `now >= expires_at`), and `WorkspaceRepository`.
- Technical ports at the root of `application/ports/`: `Clock`, `WorkspaceIdGenerator`, `SessionTokenGenerator`, `UnitOfWork` and its factory. Tests replace them with deterministic fakes.
- Tokens come from `secrets.token_urlsafe(32)` and are stored as SHA-256 hashes. A slow password hash is unnecessary because tokens carry 256 bits of randomness; lookup is by hash, so no stored value can be replayed.
- Slices: `create_workspace` (command, `POST /workspaces`) and `get_current_workspace` (query, `GET /workspaces/current`).
- The authentication provider in `dependencies.py` resolves the bearer token to a trusted `WorkspacePrincipal`. Commands and queries carry that principal; handlers reject a missing principal before touching persistence.

### 8. Local services

`infra/docker-compose.yml` runs Postgres and Qdrant with pinned versions, health checks, named volumes and `127.0.0.1` port bindings. Langfuse lives in a separate `infra/docker-compose.observability.yml` whose services all carry the `observability` profile, following its official self-hosting layout (web, worker, ClickHouse, Redis, S3-compatible storage and its own Postgres database). It starts only when both the file and the profile are selected: `docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.observability.yml --profile observability up -d --wait`. Required variables use `${VAR:?message}` so a missing value stops compose with a clear message.

*Why a separate file:* Compose interpolates required variables of services in inactive profiles too, so a single file would make the default stack demand Langfuse credentials. *Env file:* Compose reads `.env` from the compose file's folder, so commands pass `--env-file .env` for the repository file. *Storage image:* MinIO no longer publishes images on Docker Hub, so the Langfuse object store uses the Chainguard MinIO image pinned by digest.

### 9. Continuous integration

GitHub Actions with read-only permissions, actions pinned by commit SHA and a 10-minute timeout per job. Job `quality` runs lint, format check, strict typing, unit and architecture tests and strict OpenSpec validation. Job `integration` starts Postgres and Qdrant, applies migrations and runs `pytest -m integration`. The `eval` job arrives with the benchmark.

## Risks / Trade-offs

- [Async raises the learning curve] → The domain stays synchronous; tests use AnyIO; ADR 0002 records the reasoning.
- [Langfuse self-hosting is heavy] → It is optional locally; the demo hosting choice is deferred to the observability change.
- [Workspace creation has no rate limit yet] → The API is not deployed publicly before the limits change lands.
- [Ported AST rules can be bypassed by dynamic imports] → Dynamic import and execution primitives stay banned in project code, as in AgentGate.
- [Strict typing with partially typed AI libraries] → Per-module overrides are allowed only in infrastructure and workflow modules, as AGENTS.md states.

## Migration Plan

Greenfield: no data to migrate. The first migration creates `schema_migrations` and `workspaces`.

## Open Questions

- Queue technology for the worker. Deferred to its own ADR; it does not affect this change.
