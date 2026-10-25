# Architecture

`AGENTS.md` is authoritative. This page summarizes how the foundation applies it and which
executable test enforces each rule. The rules live in
[tests/architecture/rules.py](../tests/architecture/rules.py).

RAG Lab is one modular monolith: DDD for the model, CQRS and vertical slices for use cases,
hexagonal ports and adapters for I/O. Two entry points (the API today, a worker later) share one
composition root.

## Layout

```text
src/rag_lab/
  main.py            FastAPI bootstrap: settings, middleware, error handlers, feature routers
  dependencies.py    the only place concrete adapters are constructed (composition root)
  components.py      typed bundle of settings, ports and handlers built by dependencies.py
  domain/            shared/, workspaces/, rag/ (rag is maintainer-owned and still empty)
  application/       ports/ (technical), ports/rag/ (maintainer-owned), exceptions/
  features/          one folder per use case
  infrastructure/    repositories/, persistence/, gateways/, strategies/, pipelines/,
                     settings/, runtime/
  transport/         shared HTTP middleware, logging and the sanitized error envelope
tests/               domain/, application/, infrastructure/, api/, integration/, architecture/
infra/               docker-compose.yml, docker-compose.observability.yml
```

`worker.py`, `ui/`, `eval/` and `pipelines/` arrive with their own changes.

## Import matrix

| Area | May import | Third-party |
| --- | --- | --- |
| `domain/<package>` | the same package and earlier ones (`shared`, then `workspaces`, then `rag`) | none; standard library without I/O or clock reads |
| `application/` | domain, application | none |
| feature `command`, `query`, `handler`, `result`, `nodes` | domain, application, own slice (never its adapters) | none |
| feature `workflow.py` | domain, application, own slice | `langgraph` only |
| feature `endpoint.py`, `job.py` | domain, own slice, `rag_lab.dependencies` | FastAPI (endpoint) |
| feature `models.py` | domain, own `models` | Pydantic |
| `infrastructure/` | domain, application, itself | any approved library |
| `transport/` | itself, `application/exceptions` | HTTP libraries |
| `main.py`, `worker.py` | `components`, `dependencies`, `transport`, feature endpoints or jobs, `infrastructure/settings` | FastAPI |
| `dependencies.py` | everything | FastAPI providers |
| `ui/` | nothing from `rag_lab` | Streamlit, HTTP client |
| `eval/` | `rag_lab.dependencies`, feature requests, handlers and results | evaluation libraries |

Imports of every form (plain, relative, aliased, type-only, re-exported through an initializer)
are resolved before checking. Features never import sibling features. Dynamic import and
execution primitives are banned.

## Contract roles

| Role | Contract | Implementation |
| --- | --- | --- |
| Repository | `domain/<package>/repositories/`, `*Repository` | `infrastructure/repositories/` |
| Gateway | `application/ports/` or `application/ports/rag/`, `*Gateway` | `infrastructure/gateways/<kind>/` |
| Strategy, StrategyRegistry | `application/ports/rag/` | `infrastructure/strategies/<kind>/`, wired in `dependencies.py` |
| Technical port | `application/ports/`: `Clock`, `WorkspaceIdGenerator`, `SessionTokenGenerator`, `UnitOfWork`, `UnitOfWorkFactory`, `HealthProbe` | `infrastructure/runtime/`, `infrastructure/persistence/` |

Contracts are `Protocol` or `ABC`. Methods that perform I/O on repositories, gateways and probes,
and every `handle` method, are `async`. Handlers, nodes and workflows receive collaborators
through constructors and never construct concrete adapters.

## Commands and queries

| Feature | Kind | Route | Notes |
| --- | --- | --- | --- |
| `create_workspace` | command | `POST /workspaces` | unauthenticated; returns the session token once |
| `get_current_workspace` | query | `GET /workspaces/current` | bearer token; never changes state |
| `check_health` | query | `GET /health/ready` | `GET /health/live` checks no dependency |

A request that records evidence is a command. Queries never write. The workspace of a request
comes only from the bearer session token: `authenticate` in `dependencies.py` resolves it to a
`WorkspacePrincipal`, and handlers reject a missing principal before touching persistence.

## Persistence and operations

- Postgres through psycopg 3 with a connection pool, parameterized SQL and no ORM. A unit of
  work owns one connection and one transaction and rolls back unless `commit` is awaited.
- Numbered SQL files in `src/rag_lab/infrastructure/persistence/migrations/` are applied by
  `python -m rag_lab.infrastructure.persistence.migrate`, once each, with a checksum. A changed
  applied migration is refused by name. The API never migrates; readiness is 503 until the
  applied versions equal the shipped ones.
- Every response carries `X-Request-ID`; errors use `{"error": "<CODE>"}` with codes
  `UNAUTHENTICATED`, `SESSION_EXPIRED`, `NOT_FOUND`, `METHOD_NOT_ALLOWED`, `BODY_TOO_LARGE`,
  `INVALID_INPUT` and `INTERNAL_ERROR`.

## Enforcement

| Rule | Test |
| --- | --- |
| Inward imports, domain purity, slice isolation, cycles | `tests/architecture/test_boundaries.py` |
| Domain package order, `langgraph`/Pydantic/web-framework confinement, UI isolation, evaluation entry | `tests/architecture/test_frameworks.py` |
| Command and query roles, async `handle`, query purity | `tests/architecture/test_cqrs.py` |
| Constructor injection, composition only in `dependencies.py`, contract naming and placement | `tests/architecture/test_dependency_injection.py` |
| Package tree matches `AGENTS.md`, initializers define no classes | `tests/architecture/test_layout.py` |

AST checks are regression gates against accidental violations, not a sandbox.
