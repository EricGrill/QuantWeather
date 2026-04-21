# QuantWeather Monorepo

QuantWeather is a monorepo for a modular weather-market trading system targeting
Polymarket-style markets.

## Packages

- Root package: dependency-light weather-market screening, artifact generation,
  and local CLI/dashboard tooling.
- `quantweather-execution/`: execution-system starter with SQLite persistence,
  paper-trading lifecycle, approval API, and Next.js dashboard.

## Current Scope

The root screening package currently supports:

- structured market and forecast domain objects
- fixture-backed JSON normalization for markets and forecasts
- parsing threshold-style weather market rules
- generating probability estimates for temperature and precipitation events
- comparing model probabilities to market-implied prices
- sizing proposed positions under configurable risk limits
- producing auditable, reviewable opportunity summaries through a CLI entrypoint
- screening batches of markets against forecast snapshots into a ranked review feed
- exporting review feeds as stable JSON for future UI or persistence layers

The execution package currently supports:

- persisted signals, approvals, order intents, orders, fills, positions, and events
- paper-trading approval and auto-trading rules
- reconciliation and performance reporting
- stdlib HTTP API
- Next.js execution dashboard

## What Is Deliberately Deferred

The PRD calls for market discovery, NOAA ingestion, execution, monitoring,
analytics, and a dashboard. Those capabilities are intentionally deferred so the
core decision flow can be shaped and tested first.

## Quick Start

Run the test suite:

```bash
env PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```

Run the demo pipeline:

```bash
env PYTHONPATH=src python3 -m quantweather.cli
```

Screen the fixture-backed review feed:

```bash
env PYTHONPATH=src python3 -m quantweather.cli screen --format text
```

Run a screen from a JSON profile:

```bash
env PYTHONPATH=src python3 -m quantweather.cli screen --config ./quantweather-profile.json
```

Print the mixed review feed as JSON:

```bash
env PYTHONPATH=src python3 -m quantweather.cli screen --format json
```

Write the mixed review feed to disk:

```bash
env PYTHONPATH=src python3 -c "from quantweather.cli import export_fixture_screen_json; print(export_fixture_screen_json())"
```

Save the mixed review feed as a durable run with manifest metadata:

```bash
env PYTHONPATH=src python3 -m quantweather.cli save-run --run-dir ./artifacts/screen-runs
```

Save a run from a profile with CLI overrides:

```bash
env PYTHONPATH=src python3 -m quantweather.cli save-run --config ./quantweather-profile.json --min-edge 0.07
```

List saved runs from the manifest:

```bash
env PYTHONPATH=src python3 -m quantweather.cli list-runs --run-dir ./artifacts/screen-runs
```

Summarize the latest saved run:

```bash
env PYTHONPATH=src python3 -m quantweather.cli summary --run-dir ./artifacts/screen-runs
```

Compare the latest two saved runs:

```bash
env PYTHONPATH=src python3 -m quantweather.cli compare --run-dir ./artifacts/screen-runs
```

Render the latest saved run as a Markdown report:

```bash
env PYTHONPATH=src python3 -m quantweather.cli report --run-dir ./artifacts/screen-runs
```

Render the latest comparison as a Markdown report:

```bash
env PYTHONPATH=src python3 -m quantweather.cli comparison-report --run-dir ./artifacts/screen-runs
```

Write the latest run report to disk:

```bash
env PYTHONPATH=src python3 -m quantweather.cli report-save --run-dir ./artifacts/screen-runs
```

Write the latest comparison report to disk:

```bash
env PYTHONPATH=src python3 -m quantweather.cli comparison-report-save --run-dir ./artifacts/screen-runs
```

Write the latest local manual-review dashboard to disk:

```bash
env PYTHONPATH=src python3 -m quantweather.cli dashboard-save --run-dir ./artifacts/screen-runs
```

## Docker

Build the local image:

```bash
docker build -t quantweather:local .
```

Run the default demo command in a container:

```bash
docker run --rm quantweather:local
```

Run a screen from mounted local files:

```bash
docker run --rm \
  -v "$(pwd)/artifacts:/app/artifacts" \
  -v "$(pwd)/tests/fixtures:/app/tests/fixtures:ro" \
  quantweather:local \
  screen --format json
```

Use the included Compose setup:

```bash
docker compose run --rm quantweather
```

Save a run into the mounted local `artifacts/` directory:

```bash
docker compose run --rm quantweather save-run --run-dir /app/artifacts/screen-runs
```

## Package Layout

- `src/quantweather/domain.py`: shared dataclasses and enums
- `src/quantweather/ingest.py`: fixture-backed payload normalization helpers
- `src/quantweather/market_rules.py`: rule parsing for simple weather markets
- `src/quantweather/modeling.py`: probability estimation helpers
- `src/quantweather/signals.py`: market edge and opportunity ranking logic
- `src/quantweather/risk.py`: sizing and guardrails
- `src/quantweather/audit.py`: recommendation record assembly
- `src/quantweather/engine.py`: end-to-end market evaluation orchestration
- `src/quantweather/serialize.py`: JSON-safe recommendation export helpers
- `src/quantweather/storage.py`: local run history and manifest helpers
- `src/quantweather/report.py`: Markdown reporting for saved runs and comparisons
- `src/quantweather/dashboard.py`: HTML dashboard rendering for saved runs
- `src/quantweather/cli.py`: sample runnable entrypoint
- `Dockerfile` / `compose.yaml`: local container packaging for the CLI workflow
- `tests/`: regression coverage for the initial decision pipeline

## Assumptions

- The initial model treats weather inputs as already normalized forecast facts.
- Market prices are expressed as `0.0..1.0` probabilities.
- Unsupported market titles are normalized at ingest time and surfaced as
  review-feed errors during screening.
- Execution is out of scope for this first scaffold; the system only proposes
  trades.

## Profile Shape

The CLI accepts a stdlib-only JSON profile for reusable operator runs:

```json
{
  "version": 1,
  "name": "baseline",
  "run_dir": "./artifacts/screen-runs",
  "screen": {
    "markets": "./tests/fixtures/markets_mixed.json",
    "forecasts": "./tests/fixtures/forecasts.json",
    "account_balance": 5000.0,
    "sizing_method": "proportional",
    "format": "json",
    "risk_limits": {
      "max_trade_notional": 250.0,
      "max_market_exposure": 400.0,
      "max_daily_risk": 500.0,
      "min_confidence": 0.45,
      "min_edge": 0.05,
      "max_spread": 0.05,
      "min_liquidity": 5000.0
    }
  },
  "save_run": {
    "label": "screen"
  }
}
```

Override rules:

- CLI flags win over profile values.
- Profile values win over built-in defaults.
- Relative paths inside the profile are resolved relative to the profile file.
