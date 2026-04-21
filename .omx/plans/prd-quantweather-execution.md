# QuantWeather Execution System PRD

## Goal

Build a separate execution system that consumes approved weather-market signals,
manages approvals and portfolio state, places or simulates orders, and maintains
an auditable event log without coupling live execution concerns to the screening
and MCP discovery layer.

## Relationship to Existing Repos

- `mcp-civic-data`
  Owns live market discovery, NOAA enrichment, screening, saved runs, reports,
  and dashboards.
- `quantweather-execution`
  Owns approval state, execution planning, risk checks, order lifecycle,
  positions, reconciliation, and operator APIs.

The execution system should consume a stable signal contract from
`mcp-civic-data` rather than embed screening logic.

## Problem Statement

The current system can discover and screen markets, but it cannot act on them
operationally. There is no durable approval flow, no order intent model, no
portfolio ledger, and no execution adapter. Without those pieces, the project
cannot reach the PRD’s semi-automated or fully automated trading goals.

## Users

### Primary User
- Eric as operator approving and controlling capital allocation

### Secondary Users
- Developers extending execution logic and adapters
- Agents orchestrating approval and execution flows

## Core User Stories

### US-001 Approval Intake
As the operator, I want to approve or reject screened signals so that only
deliberate trades proceed toward execution.

Acceptance criteria:
- Approval decisions are persisted with actor, time, action, and rationale
- Rejected signals are not executable
- Approved signals can be converted into order intents

Priority: 1

### US-002 Paper Trading Lifecycle
As the operator, I want an end-to-end paper trading mode so that execution
logic can be validated without real capital.

Acceptance criteria:
- Order intents can be simulated into orders and fills
- Portfolio and PnL state update from simulated fills
- Reconciliation is possible after process restart

Priority: 1

### US-003 Risk Gate
As the operator, I want pre-trade risk checks so that oversized or stale trades
are blocked before they reach an exchange adapter.

Acceptance criteria:
- Per-trade and per-market limits are enforced
- Daily risk limits and a kill switch are supported
- Risk events are logged

Priority: 1

### US-004 Position and Order Ledger
As the operator, I want durable order and position state so that open exposure,
fills, and portfolio history remain auditable.

Acceptance criteria:
- Orders, fills, positions, and portfolio snapshots are persisted
- State can be queried and reconstructed deterministically

Priority: 1

### US-005 Exchange Adapter Boundary
As a developer, I want a strict adapter interface for Polymarket/CLOB so that
live execution can be added after paper trading without rewriting the core.

Acceptance criteria:
- Adapter interface is explicit
- Paper adapter and future live adapter share the same contract

Priority: 2

### US-006 Operator API
As the operator, I want a local API surface over approvals, orders, and
positions so that a future UI or automation layer can interact with the system.

Acceptance criteria:
- Minimal HTTP or service boundary exists
- API is read-only where write paths are not yet safe

Priority: 2

## Out of Scope for Initial Skeleton

- Live wallet keys or secret management
- Real order placement on Polymarket
- Portfolio optimization
- Full UI

## Architecture

### Core Modules
- `domain`
  Shared entities and enums
- `config`
  Environment/config loading
- `approvals`
  Approval decision models and services
- `orders`
  Order intents, orders, and fills
- `positions`
  Position and portfolio state
- `risk`
  Pre-trade and post-trade checks
- `events`
  Append-only audit/event log
- `repository`
  Persistence adapters
- `service`
  Orchestration entrypoints
- `api`
  Future operator API surface

### Storage
- Start with a repository boundary that can target SQLite first
- Keep schema and adapters ready for PostgreSQL later

## Delivery Order

1. Skeleton repo and domain contracts
2. Durable persistence boundary
3. Approval + paper trading flow
4. Risk and reconciliation
5. Live adapter

## Risks

- Blending screening and execution concerns would make secrets and failure modes
  harder to control
- Execution without durable approvals and reconciliation would be unsafe
- Premature live adapter work before paper lifecycle maturity would create hidden
  operational risk
