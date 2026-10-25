# ADR 0001: Modular monolith with DDD, CQRS, Vertical Slice and Hexagonal Architecture

- Status: Accepted
- Date: 2026-10-25
- Related: [AGENTS.md](../../AGENTS.md), [architecture](../architecture.md), OpenSpec change `foundation`

## Context

RAG Lab is a public learning and portfolio project: anyone uploads a document, chooses
chunking, retrieval, reranking and LLM strategies (or lets an agent choose), asks questions
and compares pipelines side by side.

Several forces shape the architecture:

- **Split authorship.** Coding agents implement infrastructure, adapters, tooling and tests
  from OpenSpec specs. The maintainer writes the RAG core by hand. Agents produce more code
  than a person can review line by line, and without boundaries a machine can check, that
  code drifts: endpoints querying the database, handlers importing concrete adapters,
  framework types leaking into the core.
- **Strategies change per request.** Chunker and embedding model are fixed when a document is
  indexed (an index profile). Retrieval mode, reranker, LLM and prompt are chosen per
  question, and a comparison runs up to three pipelines on the same question.
- **Two entry points.** An HTTP API now, and a background worker for ingestion when the queue
  arrives. Both must share the same use cases and wiring.
- **A fast-moving agent framework.** LangGraph orchestrates the router, the verifier and the
  document profiler. Its API changes often, and the node logic must stay testable without it.
- **Prior art.** [AgentGate](https://github.com/danillofratta/agentgate-sdd) already enforces
  DDD, CQRS, Vertical Slice and Hexagonal rules with AST architecture tests in a smaller,
  synchronous service.

## Decision

We will build RAG Lab as one modular monolith that combines DDD, CQRS, Vertical Slice and
Hexagonal Architecture, reusing AgentGate's conventions and architecture tests, with these
adaptations:

1. **Domain in three packages** with a fixed dependency order: `rag` may import `workspaces`
   and `shared`; `workspaces` may import `shared`; `shared` imports neither.
2. **Vertical slices.** Each use case lives in `features/<use_case>/` with role files
   (`endpoint`, `job`, `models`, `command` or `query`, `handler`, `result`, `nodes`,
   `workflow`). No centralized routes, no imports between sibling slices.
3. **CQRS without infrastructure.** Each slice is either a command or a query, over one
   Postgres database, with direct handler calls. No mediator, event bus, event sourcing or
   separate read database. A request that records evidence (a run, a cost, a quota use, a
   trace) is a command, so asking a question is a command.
4. **Hexagonal with runtime strategy selection.** Parser, Chunker, Embedder, Retriever,
   Reranker and Generator are Strategy contracts in `application/ports/rag/`. Handlers
   resolve them by name, from the resolved pipeline spec, through a `StrategyRegistry` port.
   Concrete strategies are registered only in `dependencies.py`, the single composition root.
   A new technique is one file plus one registration line.
5. **LangGraph confined to `workflow.py`.** Node logic lives in the slice's `nodes.py`,
   framework-free and constructor-injected with ports. Only `workflow.py` imports
   `langgraph`.
6. **Pipeline YAML as an adapter.** Its Pydantic schema lives in infrastructure and maps to an
   immutable domain `PipelineSpec`. The domain never sees Pydantic.
7. **Two inbound adapters, one root.** A slice exposes `endpoint.py` (HTTP), `job.py` (worker)
   or both. `main.py` and `worker.py` bootstrap their process from the same `dependencies.py`.
8. **Enforcement, not convention.**
   - AST architecture tests in Pytest check import direction (including relative, aliased,
     type-only and re-exported imports), domain package order, slice isolation, CQRS roles,
     constructor injection, framework confinement, composition only in `dependencies.py`, and
     ban dynamic import and execution.
   - `AGENTS.md` assigns code ownership by path, and OpenSpec tasks are labeled `(agent)` or
     `(human)`.
   - `.claude/settings.json` denies Claude Code edits to human-owned paths.

## Alternatives considered

- **Flat FastAPI app with a services layer.** Fastest to start and the shape of most RAG
  tutorials. Rejected: it offers no boundary a test can enforce, so agent-written code would
  couple HTTP, persistence and RAG logic, and strategy selection would grow into conditionals.
- **Architecture built around LangChain or LlamaIndex abstractions.** Rejected: they hide the
  parts this project exists to study and measure (chunking, retrieval, reranking,
  evaluation) and tie the core to fast-moving APIs. Individual strategies may still use them
  internally, behind our ports.
- **Microservices** (ingestion, query, evaluation). Rejected: deployment, networking and
  distributed-failure costs with no benefit for a single-maintainer lab. Slices give the same
  modularity in one process and can be extracted later if a real need appears.
- **Mediator or command bus, and separate read and write databases.** Rejected: ceremony
  without benefit at this size. Direct handler calls are easier to read and debug. AgentGate
  made the same choice.
- **Tactical DDD for strategies** (chunkers or retrievers as entities). Rejected: they are
  stateless algorithms with no lifecycle or invariants. Tactical DDD is kept where real
  invariants exist: workspace expiry, document ingestion state, index profile compatibility,
  run cost and quotas.
- **Ownership by instructions only.** Rejected: instructions are context for an agent, not
  enforcement. Tests and deny rules turn a violation into a failure.

## Consequences

**Positive**

- The core is testable with fakes, without FastAPI, a database or the network.
- A broken rule fails CI and names the offending file and import.
- Adding a technique is local: one strategy file, one registration line, one benchmark row.
- Each slice is a self-contained unit that fits one OpenSpec task and one agent context.

**Negative**

- More files and boilerplate than a flat app, so the first feature is slower to deliver.
- A learning curve for contributors unfamiliar with these patterns.
- The safeguards have limits. AST checks are regression gates, not a sandbox, and Claude Code
  deny rules cover its file tools and recognized shell commands, not scripts that write files
  themselves. Pull request review remains required.
- The rules live in three places (`AGENTS.md`, `tests/architecture/`, `.claude/settings.json`)
  and must change together. Changing a rule requires a new ADR.