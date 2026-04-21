# QuantWeather V1 Delivery PRD

## Goal

Use the existing QuantWeather scaffold as the base for a PRD-aligned V1 focused on manual review, signal generation, auditability, and local operator workflows for weather-market trading.

## Current Baseline

The repo already has:

- normalized market and forecast domain models
- threshold-rule parsing for supported market types
- heuristic probability estimation
- signal generation and risk-aware position sizing
- batch screening over fixture data
- JSON export for recommendations
- local run storage with manifest metadata
- run summaries, comparisons, and Markdown reports
- argparse CLI and JSON profile support for repeatable operator runs

## V1 Scope for This Repo

Given the current single-package Python repo and the no-new-dependencies constraint, V1 in this codebase will prioritize the PRD goals that can be delivered locally and cleanly:

1. Operator review workflow
2. Explainable signal generation
3. Durable local audit trail
4. Configurable risk controls
5. Local dashboard/reporting surface
6. Dockerized/local packaging

Execution against live Polymarket and live NOAA ingest are acknowledged as V1 goals in the external PRD, but in this repo they should remain adapter-shaped until credentials, API details, and dependency choices are explicitly introduced.

## User Stories

### US-001 Manual Review Dashboard
As the operator, I want a visual dashboard over saved screening runs so that I can inspect top opportunities, blocked items, and errors without reading raw JSON.

Acceptance criteria:

- A local command can generate a dashboard artifact from saved runs
- The dashboard shows latest run summary, approved opportunities, blocked items, and errors
- The dashboard links or points to saved run/report artifacts
- Regression tests cover dashboard generation

Priority: 1

### US-002 Repeatable Screening Profiles
As the operator, I want reusable JSON profiles for screening runs so that I can run consistent review configurations without long command lines.

Acceptance criteria:

- CLI supports profile loading
- CLI flags override profile values
- Invalid or missing profiles fail cleanly
- Saved run metadata captures effective config details

Priority: 1

Status: implemented in this branch

### US-003 Local Audit Trail
As the operator, I want durable saved runs, summaries, comparisons, and reports so that I can inspect how signals changed over time.

Acceptance criteria:

- Run JSON is persisted with manifest metadata
- Latest-run and comparison reports can be written to disk
- Comparison output highlights changed markets

Priority: 1

Status: implemented

### US-004 Adapter-Shaped Ingest Workflow
As a developer/operator, I want ingest boundaries that can later swap fixtures for live NOAA and market data so that the system can evolve without rewriting the core engine.

Acceptance criteria:

- Fixture loaders remain isolated
- CLI/dashboard flows consume the same normalized recommendation artifacts
- Future adapter introduction does not require changing screening/report contracts

Priority: 2

### US-005 Trade Logging and Analytics Seed
As the operator, I want saved runs and reports to expose enough structure for future PnL attribution and calibration work.

Acceptance criteria:

- Recommendation artifacts preserve reasons, model outputs, and paths to run context
- Dashboard/report surface shows enough signal detail for later postmortems

Priority: 2

### US-006 Dockerized Packaging
As the operator, I want a simple Dockerized entrypoint so that the review workflow can be run consistently in a local container.

Acceptance criteria:

- Dockerfile can run the CLI workflow
- README documents the container entrypoint

Priority: 3

## Non-goals for This Branch

- Live trading execution
- Wallet/key management
- Live weather-provider networking
- Full React dashboard
- Multi-service architecture

## Delivery Order

1. Canonical planning artifacts
2. Manual review dashboard artifact generation
3. Regression coverage and verification
4. Docker/package follow-up

## Risks

- PRD breadth exceeds what is reasonable in one uninterrupted branch without live integrations
- Operator-facing value can drift into internal tooling unless review artifacts stay human-readable
- Local artifact workflows may need concurrency hardening later
