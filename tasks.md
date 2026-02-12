# Tasks Backlog - Execution-Verified SQLClean (Incremental, Non-Breaking)

## How to Use This Backlog
- Status values: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`
- Keep all tasks tied to existing entrypoints (`sql_optimizer.py`, `sqlClean.py`, `webapp.py`)
- Do not merge a phase unless its compatibility gate tasks pass

## Phase 0 - Foundation and Refactor

| ID | Task | Files | Depends On | Status |
|---|---|---|---|---|
| P0-1 | Create package structure: `service/`, `api/`, `worker/`, `tests/` | new dirs/files | - | DONE |
| P0-2 | Extract Gemini call and SQL cleanup logic into `service/candidate_generator.py` | `sql_optimizer.py`, `service/candidate_generator.py` | P0-1 | DONE |
| P0-3 | Keep `optimize_sql(...)` as facade that calls new service module | `sql_optimizer.py` | P0-2 | DONE |
| P0-4 | Add central settings loader for env/config | `service/settings.py`, `.env.example` | P0-1 | DONE |
| P0-5 | Split dependencies into runtime/dev, add pinned versions | `pyproject.toml`, `requirements.txt` | P0-1 | DONE |
| P0-6 | Add baseline tests for current optimizer behavior | `tests/test_optimizer_baseline.py` | P0-3 | DONE |
| P0-7 | Compatibility gate: verify CLI and Streamlit still work unchanged | `sqlClean.py`, `webapp.py`, tests | P0-6 | DONE |

## Phase 1 - Multi-Candidate Rewrite Engine

| ID | Task | Files | Depends On | Status |
|---|---|---|---|---|
| P1-1 | Add candidate model (`sql`, `source`, `latency_ms`, `tokens`, `cost`) | `service/models.py` | P0-3 | TODO |
| P1-2 | Implement N-candidate generation in candidate generator | `service/candidate_generator.py` | P1-1 | TODO |
| P1-3 | Add SQL canonicalization + dedupe (`sqlglot`) | `service/normalizer.py` | P1-2 | TODO |
| P1-4 | Add additive params: `candidate_count`, `execution_verify` to `optimize_sql(...)` | `sql_optimizer.py` | P1-3 | TODO |
| P1-5 | Ensure default behavior remains single-output plain SQL | `sql_optimizer.py`, `sqlClean.py`, `webapp.py` | P1-4 | TODO |
| P1-6 | Add tests for candidate generation and dedupe | `tests/test_candidate_generator.py` | P1-3 | TODO |
| P1-7 | Compatibility gate: defaults produce same output format as today | tests | P1-5, P1-6 | TODO |

## Phase 2 - Safety + Execution Verification

| ID | Task | Files | Depends On | Status |
|---|---|---|---|---|
| P2-1 | Implement AST safety validator (allowlist/denylist/read-only) | `service/safety_validator.py` | P1-4 | DONE |
| P2-2 | Add complexity guardrails (join/subquery thresholds) | `service/safety_validator.py` | P2-1 | DONE |
| P2-3 | Add PostgreSQL explain runner (`FORMAT JSON`) | `service/plan_runner.py` | P0-4 | DONE |
| P2-4 | Add optional analyze mode with hard timeout budget | `service/plan_runner.py` | P2-3 | DONE |
| P2-5 | Build ranking engine (safety gate + cost score + tie-breakers) | `service/ranker.py` | P2-1, P2-3 | DONE |
| P2-6 | Integrate validator + runner + ranker into `optimize_sql(...)` path when `execution_verify=True` | `sql_optimizer.py` | P2-5 | DONE |
| P2-7 | Add graceful fallback when verifier DB unavailable | `sql_optimizer.py` | P2-6 | DONE |
| P2-8 | Add integration tests with dockerized/local postgres sandbox | `tests/test_execution_verify.py` | P2-6 | DONE |
| P2-9 | Compatibility gate: `execution_verify=False` path remains unchanged | tests | P2-7, P2-8 | DONE |

## Phase 3 - Backend Service API

| ID | Task | Files | Depends On | Status |
|---|---|---|---|---|
| P3-1 | Build FastAPI app skeleton + health endpoint | `api/fastapi_app.py` | P2-6 | TODO |
| P3-2 | Implement `POST /v1/optimize` sync endpoint | `api/fastapi_app.py`, `api/schemas.py` | P3-1 | TODO |
| P3-3 | Implement `POST /v1/jobs` and `GET /v1/jobs/{id}` contracts | `api/fastapi_app.py`, `api/schemas.py` | P3-1 | TODO |
| P3-4 | Add gRPC proto and service wrapper | `api/proto/*.proto`, `api/grpc_server.py` | P2-6 | TODO |
| P3-5 | Add contract tests (FastAPI vs gRPC parity) | `tests/test_api_contract.py` | P3-2, P3-4 | TODO |
| P3-6 | Add optional API mode toggle for `webapp.py` (local mode default) | `webapp.py`, `service/settings.py` | P3-2 | TODO |
| P3-7 | Compatibility gate: CLI/web local mode still works without API server | tests/manual | P3-6 | TODO |

## Phase 4 - Async, Idempotency, Rate Limits, Retries

| ID | Task | Files | Depends On | Status |
|---|---|---|---|---|
| P4-1 | Add Redis-backed job queue + worker skeleton | `worker/jobs.py`, `worker/runner.py` | P3-3 | TODO |
| P4-2 | Route async API jobs through queue and shared optimizer service | `api/fastapi_app.py`, `worker/runner.py` | P4-1 | TODO |
| P4-3 | Implement idempotency key store and middleware | `api/idempotency.py` | P3-3 | TODO |
| P4-4 | Implement per-client rate limiting middleware | `api/rate_limit.py` | P3-2 | TODO |
| P4-5 | Add bounded retries/backoff for LLM and verifier errors | `service/retry.py`, `sql_optimizer.py` | P2-6 | TODO |
| P4-6 | Add dead-letter handling and terminal failure states | `worker/jobs.py` | P4-1 | TODO |
| P4-7 | Add integration tests for idempotency/rate limit/retry behavior | `tests/test_reliability.py` | P4-6 | TODO |
| P4-8 | Compatibility gate: sync API + CLI outputs match async final results for same request | tests | P4-7 | TODO |

## Phase 5 - Observability, Benchmarks, Hardening

| ID | Task | Files | Depends On | Status |
|---|---|---|---|---|
| P5-1 | Add structured logging across optimizer stages | `sql_optimizer.py`, `api/*`, `worker/*` | P4-2 | TODO |
| P5-2 | Add OpenTelemetry tracing API->worker->verifier | `api/*`, `worker/*`, `service/*` | P4-2 | TODO |
| P5-3 | Add Prometheus metrics endpoint + custom counters/histograms | `api/fastapi_app.py`, `service/metrics.py` | P4-2 | TODO |
| P5-4 | Build benchmark harness (quality + latency + cost deltas) | `benchmarks/run_benchmarks.py`, corpus files | P2-6 | TODO |
| P5-5 | Add load tests (burst + sustained traffic) | `benchmarks/load_test.js` or `benchmarks/locustfile.py` | P3-2 | TODO |
| P5-6 | Define SLOs and alert thresholds | `docs/slo.md`, dashboards | P5-3 | TODO |
| P5-7 | Update README with architecture, metrics, and runbook | `README.md` | P5-4, P5-6 | TODO |
| P5-8 | Final compatibility gate: legacy entrypoints still operational | `sqlClean.py`, `webapp.py`, tests | P5-7 | TODO |

## Cross-Cutting Tasks

| ID | Task | Files | Depends On | Status |
|---|---|---|---|---|
| X-1 | Add `make`/script commands for test, lint, benchmark, run-api, run-worker | `Makefile` or `scripts/*.ps1` | P0-1 | TODO |
| X-2 | Add migration ADRs for key design choices | `docs/adr/*.md` | P2-6 | TODO |
| X-3 | Add CI workflow (lint + unit + integration matrix) | `.github/workflows/ci.yml` | P1-6 | TODO |
| X-4 | Create release checklist for demo and resume metrics publication | `docs/release_checklist.md` | P5-7 | TODO |

## Definition of Done (Project Level)
- `sql_optimizer.optimize_sql(...)` remains the single shared orchestration entrypoint for CLI, web, API, and worker paths.
- Existing CLI usage (`sqlclean query.sql`, stdin piping, `--repo`) remains functional.
- Existing Streamlit local mode remains functional.
- Execution-verified mode can be toggled on and produces auditable candidate ranking metadata.
- API async mode supports idempotency and rate limiting with tested reliability guarantees.
