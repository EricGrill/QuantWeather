# QuantWeather Execution

QuantWeather Execution is a starter repo for the operational side of the
weather-market trading system. It is intentionally separate from screening and
discovery so execution concerns can mature behind stricter risk, approval, and
audit boundaries.

## Scope

This starter repo does not place live trades yet. It establishes the code
structure for:

- approval decisions
- order intents
- orders and fills
- positions and portfolio state
- risk checks
- event/audit logging
- persistence boundaries

## Relationship to Other Repos

- `mcp-civic-data`
  Discovers and screens live markets, then produces reviewable signals.
- `quantweather-execution`
  Consumes approved signals and eventually executes them.

## Quick Start

Run the starter tests:

```bash
env PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```

Compile the package:

```bash
python3 -m compileall src tests
```

The starter repo now includes:

- an in-memory repository for fast unit-level work
- a SQLite-backed repository for approvals, order intents, and execution events
- paper-trading lifecycle support for orders, fills, and positions
- basic reconciliation reporting over persisted execution state
- a minimal stdlib HTTP API for health, reconciliation, and paper trading
- a dependency-free local web UI served from `/`
- JSON and printable HTML performance reports

Current SQLite URL shape:

```text
sqlite:///artifacts/execution.db
```

Run the local HTTP API and UI:

```bash
env PYTHONPATH=src python3 - <<'PY'
from quantweather_execution.api import serve
from quantweather_execution.config import load_config

server = serve(load_config(), host="127.0.0.1", port=8080)
print("QuantWeather Execution UI: http://127.0.0.1:8080")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
PY
```

## Next.js Dashboard

The repo also includes a more polished Next.js dashboard in `web/`.

Run the Python execution API in one terminal:

```bash
env PYTHONPATH=src python3 -m quantweather_execution.api --host 127.0.0.1 --port 8080
```

Run the frontend in another terminal:

```bash
cd web
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

The frontend proxies API calls through `/execution-api/*` to the Python backend
on port `8080`.

## Layout

- `src/quantweather_execution/domain.py`
- `src/quantweather_execution/config.py`
- `src/quantweather_execution/approvals.py`
- `src/quantweather_execution/orders.py`
- `src/quantweather_execution/positions.py`
- `src/quantweather_execution/risk.py`
- `src/quantweather_execution/events.py`
- `src/quantweather_execution/repository.py`
- `src/quantweather_execution/service.py`
- `src/quantweather_execution/api.py`

## Next Build Order

1. SQLite-backed repository implementation
2. Paper-trading order lifecycle
3. Approval/API surface hardening
4. Risk checks and reconciliation hardening
5. Live adapter
