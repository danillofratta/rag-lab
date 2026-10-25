# ADR 0002: Asynchronous I/O with a synchronous domain

- Status: Accepted
- Date: 2026-10-25
- Related: [ADR 0001](0001-architecture.md), OpenSpec change `foundation` (design decision 3)

## Context

- **Answering a question is mostly waiting.** A request waits on vector search, optional
  reranking through an API, and one or more LLM calls (router, generation, verifier). The CPU
  work in the request path is small, except for local models.
- **Comparison multiplies the wait.** One request runs the same question through up to three
  pipelines. Run sequentially, its latency is the sum of the pipelines; run concurrently, it
  is roughly the slowest one. For three pipelines of similar latency, that is about a third.
- **AgentGate is synchronous**, and that was the right call there: its handlers run short local
  SQLite transactions and never call remote services.
- **Synchronous endpoints hold threads.** FastAPI runs sync endpoints in a worker thread pool,
  and AnyIO's default limiter allows 40 threads per process. Each in-flight LLM call would hold
  one thread for its full duration, often several seconds, so a burst of slow questions
  exhausts the pool and queues every other synchronous request.
- **The chosen libraries are async-native.** FastAPI, psycopg 3 (`AsyncConnectionPool`), the
  Qdrant client (`AsyncQdrantClient`), LiteLLM (`acompletion`) and LangGraph (`ainvoke`) all
  offer asynchronous APIs. The foundation already uses the async Postgres pool.
- **Some work blocks.** Document parsing with Docling and local embedding and reranking models
  are CPU-bound and synchronous.

## Decision

1. Every port, handler, node, workflow and adapter that performs I/O is `async`, and every
   endpoint is `async def`.
2. The domain stays synchronous and pure. It performs no I/O, so it has nothing to await, and
   its tests stay trivial.
3. Blocking or CPU-bound work never runs on the event loop. It runs in a worker thread
   (`anyio.to_thread.run_sync`) inside the API, or in the worker process once it exists. An
   adapter that wraps a synchronous library offloads the work itself, so handlers only see
   async ports.
4. Concurrency inside a request uses AnyIO task groups. A comparison runs its pipelines in one
   task group, so a failure cancels the sibling tasks and no task outlives the request.
5. Async tests use the AnyIO pytest plugin.

## Alternatives considered

- **Synchronous code everywhere, as in AgentGate.** Simpler to read, debug and test, and FastAPI
  runs it in threads. Rejected: each slow call holds one of 40 threads, concurrent comparison
  would need hand-managed thread pools, and we would wrap the async APIs of the chosen
  libraries in synchronous calls.
- **Async only in the question slice.** Rejected: two conventions in one codebase. Shared ports
  such as the unit of work and the vector index gateway would need both versions, and the
  composition root would wire two of everything.
- **More processes instead of async.** Running more server processes adds capacity. Rejected
  as a substitute: every process loads its own copy of the local models, and it does not make a
  single comparison faster. Process scaling remains available on top of async.

## Consequences

**Positive**

- A comparison costs about as much as its slowest pipeline, not the sum of all of them.
- Waiting on the network costs a coroutine, not a thread, so one process serves many questions
  in flight.
- The code uses each library's native API, with no synchronous wrappers.

**Negative**

- Async is contagious: any function that awaits must be async, all the way up to the endpoint.
- One blocking call on the event loop (a synchronous HTTP client, `time.sleep`, heavy parsing)
  stalls every request in the process. Mitigation: synchronous libraries are used only inside
  adapters that offload them, and code review checks for blocking calls. Follow-up: enable
  Ruff's `ASYNC` (flake8-async) rules.
- Cancellation and timeouts must be explicit, for example a deadline on every LLM call.
- Tests need the AnyIO plugin, and stack traces through coroutines are harder to read.

## Validation

The expected latency gain is not measured yet. When the comparison feature lands, measure p50
and p95 latency of a three-pipeline comparison run sequentially and concurrently on the
benchmark, and record the numbers here. If concurrency does not reduce latency materially,
revisit this decision.