# Tasks

Labels follow the code ownership in `AGENTS.md`. Apply implements only `(agent)` tasks. No `(agent)` task in this change depends on a `(human)` task.

## 1. Repository bootstrap

- [x] 1.1 (agent) Add `pyproject.toml` (hatchling, `src/rag_lab`, Python >=3.12), `uv.lock`, `.gitignore`, MIT `LICENSE` and a README skeleton with setup and verification commands plus empty placeholder sections for the maintainer's narrative; verify `uv sync --locked` succeeds in a clean environment and `uv run python -c "import rag_lab"` works.
- [x] 1.2 (agent) Configure Ruff, Ruff format, strict mypy and pytest (AnyIO plugin, `integration` and `eval` markers excluded by default, outbound socket and subprocess blocking fixtures); verify fixture self-tests fail on an outbound socket and on a subprocess call, and the default test run passes on the empty package.
- [x] 1.3 (agent) Create the `src/rag_lab` package tree from `AGENTS.md` (packages only; `worker.py`, `ui/`, `eval/` and `pipelines/` arrive with their own changes), including empty initializers for the human-owned packages (`domain/rag`, `application/ports/rag`, `infrastructure/strategies`, `infrastructure/gateways/vector_index`, `infrastructure/gateways/llm`, `infrastructure/gateways/tracing`); verify the tree matches `AGENTS.md` and no initializer defines a class.
- [ ] 1.4 (agent) Add `.github/workflows/ci.yml` with the `quality` and `integration` jobs from design decision 9; verify both jobs run every documented gate and a deliberately failing gate fails its job.

## 2. Architecture gates

- [x] 2.1 (agent) Port `tests/architecture/` from AgentGate with the root package name as a single constant; verify every ported positive and negative fixture passes against RAG Lab paths.
- [x] 2.2 (agent) Add the rules in design decision 2 (domain package order, feature role files including `job`, `nodes` and `workflow`, `langgraph` confinement, Pydantic confinement, composition only in `dependencies.py`, UI isolation, evaluation entry); verify each rule with at least one passing and one failing fixture, covering plain, relative, aliased, type-only and re-exported imports.
- [x] 2.3 (agent) Write `docs/architecture.md` (layout, import matrix, contract roles, command and query map) consistent with `AGENTS.md`; verify every path, command and rule it names exists in the repository or is enforced by an architecture test.

## 3. Local services and configuration

- [x] 3.1 (agent) Add `infra/docker-compose.yml` (design decision 8) and `.env.example` with placeholders only; verify `docker compose up -d --wait` reports Postgres and Qdrant healthy, data survives a restart, no observability service runs without the profile, the profile starts Langfuse healthy, and a missing required variable stops compose with a message naming it.
- [x] 3.2 (agent) Implement typed settings in `infrastructure/settings/` with fail-fast validation; verify tests for missing, malformed and out-of-range values (including a non-positive workspace lifetime) exit with the setting name and never print a secret value.
- [ ] 3.3 (agent) Implement the async connection pool, unit of work and migration command (design decision 4) with the first migration creating `schema_migrations`; verify integration tests: migrations apply in order once, a second run applies nothing, a changed applied migration is refused by name, and a rolled-back unit of work leaves no rows.

## 4. API runtime

- [x] 4.1 (agent) Implement `main.py`, `dependencies.py` and `components.py` with lifespan-managed resources, plus the transport middleware from design decision 6; verify API tests for request IDs on success and failure, 413 `BODY_TOO_LARGE` on declared and streamed bodies with the handler not invoked, 422 `INVALID_INPUT` without echoed input, 500 `INTERNAL_ERROR` without exception text, and log capture showing no authorization header, token or body.
- [ ] 4.2 (agent) Implement the `check_health` query slice and the `HealthProbe` port and adapter; verify liveness returns 200 with the database down, readiness returns 200 when migrated, and 503 without error details when the database is unreachable or migrations are pending.
- [x] 4.3 (agent) Serve OpenAPI documentation only when enabled by settings; verify the documentation routes return 200 when enabled and 404 when disabled.

## 5. Workspace sessions

- [x] 5.1 (agent) Implement `domain/shared` and `domain/workspaces` (design decision 7) and the technical ports `Clock`, `WorkspaceIdGenerator`, `SessionTokenGenerator`, `UnitOfWork` and its factory; verify pure domain tests for the expiry boundary (expired when now equals expiry), invalid identifiers and invalid hashes, with no I/O.
- [ ] 5.2 (agent) Implement the `create_workspace` command slice, the Postgres `WorkspaceRepository` and its migration; verify API tests for 201 with identifier, token and expiry equal to creation plus the configured lifetime, 422 on unknown fields, and an integration test showing only the token hash is stored.
- [x] 5.3 (agent) Implement bearer session authentication in `dependencies.py` and the `get_current_workspace` query slice; verify identical 401 `UNAUTHENTICATED` bodies for missing, malformed and unknown tokens, 401 `SESSION_EXPIRED` at the expiry instant under a fake clock, unchanged expiry after repeated requests, no stored change after repeated inspection, a direct handler call without a principal rejected before persistence access, and an OpenAPI check that no workspace-scoped endpoint accepts a workspace identifier.
- [ ] 5.4 (agent) Add sentinel tests that create workspaces and scan responses, logs, error bodies and stored rows; verify the generated token appears only in its creation response.

## 6. Maintainer decisions

- [ ] 6.1 (human) Write `docs/adr/0001-architecture.md` (patterns adopted from AgentGate and the RAG Lab adaptations) and `docs/adr/0002-async-io.md`; verify each records context, decision, alternatives considered and consequences.
- [ ] 6.2 (human) Review the ported architecture rules and the workspace slices against `AGENTS.md`; verify by approving the pull request.

## 7. Final verification

- [ ] 7.1 (agent) Run every gate in `AGENTS.md` in a clean environment plus the integration suite against the compose stack; verify all pass and record the commands and results in the pull request description.
