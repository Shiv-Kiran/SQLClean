# Execution-Verified SQL Optimization Service - Implementation Plan

## 1. Goal
Transform `SQLClean` from a prompt-only SQL refactoring tool into a production-grade backend system that:
- generates multiple SQL rewrite candidates,
- validates candidate safety,
- executes `EXPLAIN` or `EXPLAIN ANALYZE` against a sandbox database,
- automatically selects the safest, lowest-cost candidate,
- exposes this workflow over reliable API interfaces.

## 1.1 Non-Negotiable Compatibility Constraints
This roadmap is incremental and must stay connected to existing code:
- Keep `sql_optimizer.optimize_sql(...)` as the stable entrypoint used by both `sqlClean.py` and `webapp.py`.
- Keep CLI behavior and flags backward compatible while new features are introduced behind optional parameters.
- Keep `rag_utils.py`, `hybrid_rag.py`, and `rag_config.py` as active retrieval modules; new service code must call them, not replace them abruptly.
- Avoid big-bang rewrites. Every phase must compile and run with current interfaces before adding the next layer.

## 2. Problem Statement
Current flow is single-shot rewrite + syntax check. This leaves two major gaps:
- no execution-level verification of performance claims,
- no backend service primitives expected in AI systems roles (async orchestration, rate limits, idempotency, retries, observability).

## 3. Scope
### In Scope
- Multi-candidate rewrite generation (N candidates per query)
- SQL AST safety guardrails (read-only, blocked statements, dangerous functions)
- Plan evaluation using PostgreSQL `EXPLAIN (FORMAT JSON)` and optional `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` in sandbox
- Candidate ranking and auto-selection
- FastAPI endpoint layer
- gRPC service layer (parity for core optimize flow)
- Async job queue with worker processes
- Rate limiting, retry policies, idempotency keys
- Metrics, tracing, structured logs, benchmark harness

### Out of Scope (Phase 1)
- Full semantic equivalence proofs for all SQL constructs
- Production DB execution for arbitrary user queries
- Multi-dialect execution verification beyond PostgreSQL

## 4. Target Architecture
```text
Client (CLI/Web/SDK)
  -> API Gateway (FastAPI/gRPC)
    -> Request Orchestrator
      -> Retrieval Context Builder (existing RAG modules)
      -> Candidate Generator (LLM, N variants)
      -> Safety Validator (AST/static checks)
      -> Execution Verifier (EXPLAIN sandbox)
      -> Ranker + Selector (cost + risk scoring)
      -> Result Store (jobs, metadata, idempotency)
    -> Async Queue (Redis + workers)
      -> Background optimization/evaluation jobs
Observability Stack:
  Metrics + Tracing + Structured Logs + Alerts
```

## 4.1 Migration Mapping: Existing Files -> New Responsibilities
- `sql_optimizer.py`
  - stays as orchestration facade,
  - gains feature flags (`execution_verify`, `candidate_count`, `mode`),
  - delegates to new modules instead of embedding all logic inline.
- `sqlClean.py`
  - remains the CLI entrypoint,
  - adds optional flags for verification mode while preserving old command usage.
- `webapp.py`
  - initially continues direct call to `optimize_sql`,
  - later switches to API client mode without breaking local mode.
- `rag_utils.py` / `hybrid_rag.py` / `rag_config.py`
  - reused as retrieval context providers for candidate prompts.
- New modules (incremental):
  - `service/candidate_generator.py`
  - `service/safety_validator.py`
  - `service/plan_runner.py`
  - `service/ranker.py`
  - `api/fastapi_app.py`
  - `worker/jobs.py`

## 5. Design Decisions
1. Database target for verification: PostgreSQL 16 (single dialect first).
2. Safety-first mode:
- allow only `SELECT`/CTE read-only queries in initial release,
- block DDL/DML and risky statements before execution.
3. Ranking strategy:
- hard safety gate first,
- then performance score (`total_cost`, estimated rows, memory, timing if analyze enabled),
- deterministic tie-breakers (shorter plan, fewer scans, simpler join tree).
4. API semantics:
- synchronous small jobs and async job mode,
- idempotency required for async submit endpoints.
5. Reliability primitives:
- retry with exponential backoff on transient LLM and DB errors,
- fail fast on validation/safety violations,
- explicit timeout budgets per stage.

## 6. Implementation Phases

## Phase 0 - Foundation and Refactor (Week 1)
### Deliverables
- New package layout (`service/`, `api/`, `worker/`) while keeping top-level entrypoints unchanged
- Central config management (env-driven settings)
- Dependency hygiene (pin/runtime vs dev dependencies)
- Existing optimizer logic moved behind service interfaces without removing `optimize_sql(...)`

### Concrete Integration Steps
- Extract existing Gemini + defensive logic from `sql_optimizer.py` into `service/candidate_generator.py`.
- Keep `sql_optimizer.optimize_sql(...)` as a thin orchestrator wrapper calling new modules.
- Add a legacy-mode path in `optimize_sql(...)` that returns current behavior by default.

### Exit Criteria
- Existing CLI flow still works using refactored internals.
- Existing Streamlit flow still works unchanged from user perspective.
- Unit tests pass for baseline behavior.

## Phase 1 - Multi-Candidate Rewrite Engine (Week 2)
### Deliverables
- Candidate generator returns K unique rewrites per input
- Canonicalization and dedupe pass (`sqlglot` normalize)
- Candidate metadata model (source prompt, token/cost, generation latency)

### Concrete Integration Steps
- Add optional params to `optimize_sql(...)`:
  - `candidate_count: int = 1`
  - `execution_verify: bool = False`
- If `candidate_count=1`, preserve current single-output behavior.
- If `candidate_count>1`, return the top candidate plus metadata in structured mode (for API/internal use), plain SQL for CLI default mode.

### Exit Criteria
- Given one SQL input, system consistently produces >=3 parseable candidates in happy path.
- CLI and web app still produce one final SQL output by default.

## Phase 2 - Safety and Execution Verification (Weeks 3-4)
### Deliverables
- AST safety validator:
  - statement-type allowlist,
  - banned operation/function checks,
  - complexity thresholds (max joins, subquery depth)
- Plan runner:
  - `EXPLAIN (FORMAT JSON)` for all candidates,
  - optional `ANALYZE` mode in isolated transaction/session
- Scoring/ranking engine with auditable decision output

### Concrete Integration Steps
- Implement `service/safety_validator.py` using `sqlglot` AST checks and plug into `sql_optimizer.optimize_sql(...)`.
- Implement `service/plan_runner.py` and call only when `execution_verify=True`.
- Introduce safe fallback in `sql_optimizer.py`: if DB verifier is unavailable, return best syntax-valid candidate and include verification status note.

### Exit Criteria
- Every returned winner has:
  - parse success,
  - safety pass,
  - explain plan metadata,
  - deterministic score record.
- Legacy mode (`execution_verify=False`) remains fully functional.

## Phase 3 - Backend Service API (Week 5)
### Deliverables
- FastAPI endpoints:
  - `POST /v1/optimize` (sync)
  - `POST /v1/jobs` (async submit)
  - `GET /v1/jobs/{job_id}` (status/result)
- Request/response contracts with versioning
- gRPC proto and service for optimize flow

### Concrete Integration Steps
- Build API layer as wrappers around `sql_optimizer.optimize_sql(...)` first, then move to lower-level modules once stable.
- Keep CLI/web local mode active while API mode is introduced.
- Add optional API-client path in `webapp.py` controlled by config flag.

### Exit Criteria
- API + gRPC pass contract tests and return equivalent business results.
- Existing CLI command (`sqlclean file.sql --repo ...`) still works exactly as before.

## Phase 4 - Async, Idempotency, Rate Limits, Retries (Week 6)
### Deliverables
- Queue-backed worker pipeline (Redis + Celery/RQ/Arq)
- Idempotency key middleware/store
- Rate limiter (token bucket/leaky bucket via Redis)
- Stage-level retries with bounded backoff and dead-letter handling

### Concrete Integration Steps
- Start with async only in API path; CLI and web local path remain synchronous.
- Worker code calls the same orchestration service used by sync path to avoid divergent logic.
- Add retries in shared service layer, not only in API handlers.

### Exit Criteria
- Duplicate submit with same idempotency key is deduplicated.
- System enforces per-client rate limits.
- Transient failures are retried and logged with final terminal states.
- Sync and async produce equivalent ranking decisions for same input and config.

## Phase 5 - Observability, Benchmarks, Hardening (Weeks 7-8)
### Deliverables
- OpenTelemetry tracing across API -> worker -> DB verifier
- Prometheus metrics:
  - request counts, latency percentiles,
  - candidate generation stats,
  - safety reject rate,
  - verification success/failure,
  - plan cost reduction distribution
- Benchmark suite with representative SQL corpus
- Load test profile and SLOs

### Concrete Integration Steps
- Add structured event logs inside `sql_optimizer.py` orchestration points to include legacy and API paths.
- Benchmark both:
  - legacy mode (single rewrite),
  - execution-verified mode (multi-candidate + explain ranking),
  to prove incremental value.

### Exit Criteria
- Dashboard + benchmark report committed.
- SLOs defined and measurable.
- Regression tests show no behavioral break for existing CLI/web default paths.

## 7. Testing Strategy
1. Unit tests:
- parser/safety rules,
- scoring/ranking logic,
- idempotency/rate-limit middleware behavior.
2. Integration tests:
- local PostgreSQL sandbox explain runner,
- API + queue + worker end-to-end.
3. Contract tests:
- FastAPI and gRPC response parity.
4. Load tests:
- throughput, p95/p99 latency, queue depth behavior under burst traffic.

## 7.1 Compatibility Test Matrix (Must Pass Every Phase)
- `sqlClean.py` file input flow
- `sqlClean.py` stdin pipe flow
- `webapp.py` local optimize flow
- `optimize_sql(...)` with and without `repo_path`
- `optimize_sql(...)` with both `RAGStrategy.SIMPLE` and `RAGStrategy.HYBRID`

## 8. Success Metrics (Resume-Relevant)
- Syntax-valid candidate rate >= 99%
- Safety rejection precision (manual sample) >= 95%
- Median explain-plan cost reduction >= 20% vs baseline input
- Async submit dedupe success = 100% for identical idempotency keys
- API p95 latency targets:
  - sync optimize <= 2.5s (without analyze)
  - async submit <= 300ms
- End-to-end trace coverage >= 95% of requests

## 9. Risks and Mitigations
1. LLM variability causes unstable rewrites:
- Mitigation: deterministic temperature defaults, stricter output schema, candidate normalization.
2. Explain plan does not guarantee runtime speedup:
- Mitigation: keep `ANALYZE` optional mode for benchmark datasets and report both estimated and observed metrics.
3. Safety edge cases in SQL parsing:
- Mitigation: explicit denylist + extensive fuzz and regression tests.
4. Queue/worker operational complexity:
- Mitigation: start with one broker and one worker type, add dead-letter and replay tooling early.

## 9.1 Migration-Specific Risks
1. Divergent logic between legacy path and API path:
- Mitigation: enforce one shared orchestration service called by CLI, web, API, and worker.
2. Breaking existing function signatures:
- Mitigation: additive parameters only; no removals until deprecation cycle documented.
3. RAG regressions during refactor:
- Mitigation: keep `rag_config.py` factory entrypoint stable and covered by integration tests.

## 10. Deliverable Artifacts
- `implementation_plan.md` (this file)
- `tasks.md` (execution backlog)
- ADRs for key decisions:
  - verifier database choice,
  - queue system,
  - idempotency strategy,
  - scoring formula.
- Benchmark report and architecture diagram for README.
