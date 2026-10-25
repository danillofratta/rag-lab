# Proposal

## Why

RAG Lab needs an enforced base before any retrieval code exists: a reproducible toolchain, architecture rules that keep coding agents inside their boundaries, local services, a running API, persistence and anonymous workspaces that isolate visitors. Building it first lets the human-owned RAG core start on solid ground and keeps every later change reviewable.

## What Changes

- Python 3.12 project with locked dependencies, linting, formatting, strict typing, isolated unit tests and OpenSpec validation, all enforced in CI.
- Architecture tests ported from AgentGate (`github.com/danillofratta/agentgate-sdd`, `tests/architecture/`) and extended to the RAG Lab rules in `AGENTS.md`: domain package order, slice isolation, command/query roles, constructor injection, LangGraph confined to `workflow.py`, concrete strategies wired only in the composition root, and a UI that never imports the package.
- Local services: Postgres and Qdrant by default, Langfuse behind an optional `observability` profile.
- Typed settings validated at startup, with placeholder-only example configuration.
- API runtime: application factory, feature-local routes, request IDs, request body limit, sanitized error envelope, structured logs, liveness and readiness reporting, optional OpenAPI docs.
- Postgres persistence: connection pooling, unit of work and checksummed, ordered schema migrations.
- Anonymous workspace sessions: a visitor creates a workspace, receives a session token once, and every later request is scoped to that workspace until it expires.
- Empty packages for the human-owned RAG core, so the maintainer can start the domain and ports immediately.
- Out of scope: document upload, indexing, questions, the worker and queue technology, rate limiting, workspace cleanup, UI and deployment. Each arrives in its own change.

## Capabilities

### New Capabilities

- `development-harness`: reproducible toolchain, quality gates, test isolation and executable architecture rules.
- `local-infrastructure`: local service stack, configuration validation and database schema management.
- `service-runtime`: API process behavior shared by every feature: health reporting, request identification, size limits, sanitized errors and logging.
- `workspace-sessions`: anonymous workspaces with expiring session tokens that scope every later request.

### Modified Capabilities

None. The repository is new.

## Impact

Adds `pyproject.toml`, `uv.lock`, `src/rag_lab/`, `tests/`, `infra/docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml`, `docs/architecture.md`, an MIT `LICENSE` and a README skeleton. Runtime dependencies are limited to the web framework, settings and validation, the ASGI server and the Postgres driver; no LLM, vector database client or agent framework is added yet. The human maintainer records the architecture and asynchronous I/O decisions as the first ADRs.
