# RAG Lab

An open retrieval-augmented generation lab: upload documents, choose (or let an
agent choose) chunking, retrieval, reranking and LLM strategies, then compare
pipeline configurations side by side with citations, scores, latency and cost.

## Why this project exists

<!-- Maintainer narrative: motivation and goals. -->

## Architecture

<!-- Maintainer narrative: the decisions behind the design. See docs/architecture.md
for the layout and dependency rules, and docs/adr/ for recorded decisions. -->

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer.

```bash
uv sync --locked
cp .env.example .env   # then replace every placeholder
```

## Verification

```bash
uv run --locked pytest -m "not integration and not eval"
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy --strict src
openspec validate --all --strict
```

Integration tests need the local services:

```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
uv run --locked python -m rag_lab.infrastructure.persistence.migrate
uv run --locked pytest -m integration
```

Optional Langfuse observability stack (heavy; off by default):

```bash
docker compose --env-file .env -f infra/docker-compose.yml \
  -f infra/docker-compose.observability.yml --profile observability up -d --wait
```

## Running the API

```bash
uv run --locked python -m rag_lab.infrastructure.persistence.migrate
uv run --locked uvicorn rag_lab.main:create_app --factory --no-access-log
```

The API logs its own structured access line and never migrates by itself. Interactive docs are
served only with `RAG_LAB_DOCS_ENABLED=true`. On Windows, psycopg needs the selector event
loop, so run the server from WSL or Docker there.

## Results and lessons learned

<!-- Maintainer narrative: benchmark results and what the project taught. -->

## License

MIT, see [LICENSE](LICENSE).
