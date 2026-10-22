# QuantWeather MVP Acceptance Checklist

This document defines what "done enough to use" means for QuantWeather. An
operator can run these checks in one sitting to verify the working-product loop.

**Scope:** Paper trading only. Live-money trading is explicitly out of scope
until the paper loop is proven reliable.

---

## MVP Acceptance Items

### 1. Live Weather Markets Available

**What it verifies:** The system can discover and display current weather
markets from a live exchange with prices, liquidity, and spreads.

**How to check:**

```bash
env PYTHONPATH=src python3 -m quantweather.cli discover \
  --min-liquidity 5000 \
  --format json
```

**Passing looks like:**

- Command returns JSON with one or more market entries
- Each entry includes `market_id`, `yes_price`, `no_price`, `liquidity`, `spread`
- Markets have weather-related titles (temperature, precipitation)

**Works today:** Partially. Fixture-backed discovery works. Live Polymarket
discovery requires [CHA-2903](https://linear.app/chainbytes/issue/CHA-2903) and
[GitHub #2](https://github.com/EricGrill/QuantWeather/issues/2).

---

### 2. Live Forecast Ingestion

**What it verifies:** The system can fetch and normalize live NOAA/NWS forecasts
for locations relevant to discovered markets.

**How to check:**

```bash
env PYTHONPATH=src python3 -m quantweather.cli ingest-noaa \
  --lat 40.7128 \
  --lon -74.0060 \
  --location "New York City" \
  --user-agent "QuantWeather/0.1 contact=you@example.com" \
  --format json
```

**Passing looks like:**

- Command returns JSON with forecast snapshot
- Contains `temperature_high_f`, `precipitation_probability`, `precipitation_in`
- Forecast `observed_at` is recent (within 24 hours)

**Works today:** Yes. Live NOAA fetch path is implemented via NWS points API.

---

### 3. Model Edge Calculation

**What it verifies:** Given markets and forecasts, the system calculates
probability estimates and identifies trading edge.

**How to check:**

```bash
env PYTHONPATH=src python3 -m quantweather.cli screen \
  --markets ./tests/fixtures/markets_mixed.json \
  --forecasts ./tests/fixtures/forecasts.json \
  --min-edge 0.05 \
  --format json
```

**Passing looks like:**

- Output contains recommendation records
- Records with `final_status: "approved"` have positive `edge` values
- Each record includes `model_probability_yes`, `market_probability_yes`, and
  `signal_side`
- Blocked/error records explain why via `reason_codes`

**Works today:** Yes. Fixture-backed screening fully implemented.

---

### 4. Paper Trade Execution

**What it verifies:** Approved signals can be executed in paper-trading mode,
creating persistent orders, fills, and positions.

**How to check:**

```bash
# Save a screening run
env PYTHONPATH=src python3 -m quantweather.cli save-run \
  --run-dir ./artifacts/screen-runs

# Execute paper trades from the saved run
env PYTHONPATH=src python3 -m quantweather.cli execute \
  --run-dir ./artifacts/screen-runs \
  --mode paper
```

**Passing looks like:**

- Execution artifact created at `artifacts/screen-runs/execution-*.json`
- Orders with `status: "paper_filled"` for approved recommendations
- Skipped orders explain why via `reason_codes`

**Works today:** Yes. Paper execution artifacts are generated from saved runs.

---

### 5. Visible P/L and Audit Trail

**What it verifies:** The operator can inspect trade history, portfolio state,
and realized P/L through a durable audit log.

**How to check:**

```bash
# Start the execution API/UI
cd quantweather-execution
env PYTHONPATH=src python3 -m quantweather_execution.api --host 127.0.0.1 --port 8080 &

# Check reconciliation state
curl -s http://127.0.0.1:8080/reconcile | python3 -m json.tool

# Check performance report
curl -s http://127.0.0.1:8080/report | python3 -m json.tool

# Or view the HTML report
open http://127.0.0.1:8080/report.html
```

**Passing looks like:**

- `/reconcile` returns `healthy: true` with counts for approvals, orders, fills,
  positions
- `/report` shows `realized_pnl`, `wins`, `losses`, `open_exposure`
- No orphan orders or fills in reconciliation

**Works today:** Yes for paper trades ingested via the execution API. Requires
manual signal ingest or [CHA-2904](https://linear.app/chainbytes/issue/CHA-2904)
for automated screening-to-execution handoff.

---

### 6. Health and Monitoring Status

**What it verifies:** The operator can verify system health at a glance,
including screening run quality and execution state.

**How to check:**

```bash
# Monitor latest screening run
env PYTHONPATH=src python3 -m quantweather.cli monitor \
  --run-dir ./artifacts/screen-runs

# Check execution health
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/reconcile
```

**Passing looks like:**

- Monitor output shows `healthy: true` for screen and execution (if present)
- No `critical` severity alerts
- Error rate below 25%, blocked rate below 75%
- `/health` returns `status: "ok"`

**Works today:** Yes. Monitoring checks implemented for screen runs and
execution orders.

---

### 7. Local Operator Dashboard

**What it verifies:** The operator can review all of the above in a single
visual interface without reading raw JSON.

**How to check:**

```bash
# Generate dashboard artifact
env PYTHONPATH=src python3 -m quantweather.cli dashboard-save \
  --run-dir ./artifacts/screen-runs

# Open the generated HTML file
open artifacts/screen-runs/dashboard-*.html
```

**Passing looks like:**

- Dashboard shows saved runs count, latest run summary
- Approved/blocked/error sections with market details and reason codes
- Run history table with linked artifacts
- Monitoring section with health status
- Analytics section with approval rate, average edge

**Works today:** Yes. HTML dashboard generation fully implemented.

---

## Summary Table

| # | Check                        | Works Today | Blocking Issues                                      |
|---|------------------------------|-------------|------------------------------------------------------|
| 1 | Live weather markets         | Partial     | [CHA-2903], [GH#2], [CHA-2902]                       |
| 2 | Live forecast ingestion      | Yes         | —                                                    |
| 3 | Model edge calculation       | Yes         | —                                                    |
| 4 | Paper trade execution        | Yes         | —                                                    |
| 5 | Visible P/L and audit trail  | Yes         | [CHA-2904] for automated handoff                     |
| 6 | Health and monitoring status | Yes         | [CHA-2902] for venue status visibility               |
| 7 | Local operator dashboard     | Yes         | —                                                    |

[CHA-2902]: https://linear.app/chainbytes/issue/CHA-2902
[CHA-2903]: https://linear.app/chainbytes/issue/CHA-2903
[CHA-2904]: https://linear.app/chainbytes/issue/CHA-2904
[GH#2]: https://github.com/EricGrill/QuantWeather/issues/2

---

## What Blocks MVP Completion

The foundation is in place. To complete the MVP loop end-to-end with live data:

1. **CHA-2902** — Venue configuration and runtime status so the operator knows
   whether Polymarket is configured/dry-run/ready/error.

2. **CHA-2903** — Live Polymarket market data adapter so screening operates on
   real markets instead of fixtures.

3. **CHA-2904** — Screening-to-execution signal handoff so approved signals
   automatically flow into the execution system.

Once those three issues are resolved, an operator can run the full loop:

```
Live Polymarket markets
      ↓
Live NOAA forecasts
      ↓
Edge calculation + screening
      ↓
Signal handoff to execution
      ↓
Paper trade approval
      ↓
Position + P/L tracking
      ↓
Dashboard review
```

---

## Out of Scope for MVP

- Live-money trading (requires exchange adapter, wallet/key management)
- Multi-venue support beyond Polymarket
- Production monitoring transports (metrics, alerting)
- Authentication and multi-user access
- PostgreSQL or other production databases
- Full React dashboard (stdlib UI is sufficient for MVP)

These remain deferred until the paper-trading loop is proven reliable.
