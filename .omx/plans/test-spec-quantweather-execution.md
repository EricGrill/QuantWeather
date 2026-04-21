# QuantWeather Execution System Test Spec

## Verification Strategy

The execution system should start with narrow, deterministic tests around pure
domain logic and repository behavior before any live exchange work is attempted.

## Initial Test Layers

### Unit Tests

- domain entity construction and enum behavior
- approval decision state transitions
- order intent creation
- risk gate checks for trade size, stale inputs, and kill switch behavior
- position aggregation from fills

### Repository Tests

- record and retrieve approval decisions
- record order intents, orders, fills, and positions
- deterministic latest-state reconstruction

### Service Tests

- approved signal -> order intent
- rejected signal -> no intent
- paper-trading execution updates orders and positions
- risk rejection emits a risk event

### Future Integration Tests

- execution service consuming a saved/screened signal payload from `mcp-civic-data`
- live adapter contract tests against mocked Polymarket/CLOB responses

## Acceptance Checks for the Starter Repo

- project imports cleanly
- starter tests pass
- package layout supports future separation of domain, persistence, and service
- README explains the repo boundary and intended build order

## Quality Gates

- unit tests green
- import smoke tests green
- compileall green

## Non-goals for the Starter Repo

- live exchange integration tests
- end-to-end UI tests
- secret management tests
