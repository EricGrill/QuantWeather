from __future__ import annotations


def render_operator_ui() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QuantWeather Execution Console</title>
  <style>
    :root {
      --ink: #17211f;
      --muted: #60706b;
      --paper: #fbf6ea;
      --card: #fffdf7;
      --line: #d9cfbb;
      --green: #2f6f4e;
      --amber: #a86f18;
      --blue: #244d68;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at 10% 10%, rgba(47,111,78,0.16), transparent 28rem),
        linear-gradient(135deg, #f7efe0, #e9dfcd);
      color: var(--ink);
    }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 32px 22px 64px; }
    .hero {
      background: linear-gradient(135deg, #14312e, #2e6154);
      color: #fff8e8;
      padding: 28px;
      border-radius: 22px;
      box-shadow: 0 14px 38px rgba(20, 49, 46, 0.22);
    }
    .hero h1 { margin: 0 0 8px; font-size: clamp(32px, 5vw, 56px); line-height: 0.95; }
    .hero p { margin: 0; max-width: 760px; color: #e8ddc8; font-size: 18px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 22px 0; }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 8px 24px rgba(23, 33, 31, 0.06);
    }
    .stat { font-size: 34px; font-weight: 700; }
    .muted { color: var(--muted); }
    button {
      border: 0;
      border-radius: 999px;
      padding: 10px 15px;
      background: var(--blue);
      color: #fff;
      cursor: pointer;
      font-weight: 700;
    }
    button.secondary { background: var(--green); }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      background: #fffefa;
      color: var(--ink);
      font: inherit;
    }
    textarea { min-height: 190px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { text-align: left; border-bottom: 1px solid var(--line); padding: 10px 8px; vertical-align: top; }
    th { color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: 0.04em; }
    code { background: #efe6d3; padding: 2px 5px; border-radius: 6px; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 780px) { .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <h1>QuantWeather Execution Console</h1>
      <p>Local paper-trading control surface for signal intake, approvals, and reconciliation.</p>
    </section>

    <section class="grid" id="stats"></section>

    <section class="row">
      <div class="card">
        <h2>Ingest Signal</h2>
        <textarea id="signalPayload"></textarea>
        <p><button onclick="ingestSignal()">Store Signal</button></p>
      </div>
      <div class="card">
        <h2>Approve Signal</h2>
        <textarea id="approvalPayload"></textarea>
        <p><button class="secondary" onclick="approveSignal()">Approve + Paper Trade</button></p>
      </div>
    </section>

    <section class="row">
      <div class="card">
        <h2>Performance Report</h2>
        <div id="reportSummary"></div>
      </div>
      <div class="card">
        <h2>Recent Events</h2>
        <div id="events"></div>
      </div>
    </section>

    <section class="card">
      <h2>Open Trades</h2>
      <p class="muted">Every approved paper trade appears here immediately.</p>
      <div id="openTrades"></div>
    </section>

    <section class="card">
      <h2>Positions / Outcome Tracking</h2>
      <p class="muted">Settle markets below to see which paper trades would have paid off.</p>
      <div id="positions"></div>
    </section>

    <section class="card">
      <h2>Signals</h2>
      <div id="signals"></div>
    </section>

    <section class="card">
      <h2>Settle Market</h2>
      <textarea id="settlementPayload"></textarea>
      <p><button onclick="settleMarket()">Settle Outcome</button></p>
    </section>

    <section class="card">
      <h2>Auto Paper Trade Rules</h2>
      <textarea id="autoTradePayload"></textarea>
      <p><button class="secondary" onclick="autoTrade()">Evaluate + Paper Trade Matching Signals</button></p>
    </section>

    <section class="card">
      <h2>Latest Response</h2>
      <pre id="output" class="muted">Ready.</pre>
    </section>
  </main>
  <script>
    const now = "2026-04-20T18:30:00Z";
    const sampleSignal = { signal_id: "sig-ui-1", market_id: "mkt-ui-1", title: "NYC high at or above 80F?", side: "YES", edge: 0.12, confidence: 0.75, proposed_notional: 100.0, source_run_id: "run-ui-1", created_at: now };
    const sampleApproval = { signal_id: "sig-ui-1", decision: { signal_id: "sig-ui-1", status: "approved", decided_at: "2026-04-20T18:31:00Z", actor: "eric", rationale: "looks good" }, risk_limits: { max_order_notional: 500.0 }, created_at: "2026-04-20T18:31:00Z", intent_id: "intent-ui-1", order_id: "order-ui-1", fill_id: "fill-ui-1" };
    const sampleSettlement = { market_id: "mkt-ui-1", winning_side: "YES", created_at: "2026-04-20T19:00:00Z" };
    const sampleAutoTrade = { created_at: "2026-04-20T18:35:00Z", min_edge: 0.05, min_confidence: 0.45, max_notional: 250.0, max_order_notional: 500.0, actor: "auto-paper-trader" };
    signalPayload.value = JSON.stringify(sampleSignal, null, 2);
    approvalPayload.value = JSON.stringify(sampleApproval, null, 2);
    settlementPayload.value = JSON.stringify(sampleSettlement, null, 2);
    autoTradePayload.value = JSON.stringify(sampleAutoTrade, null, 2);
    async function api(path, options = {}) { const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options }); return response.json(); }
    function show(payload) { output.textContent = JSON.stringify(payload, null, 2); }
    async function refresh() {
      const [health, reconcile, signalData, tradeData, report] = await Promise.all([api("/health"), api("/reconcile"), api("/signals"), api("/trades"), api("/report")]);
      stats.innerHTML = [["Health", health.status], ["Approvals", reconcile.approval_count], ["Orders", reconcile.order_count], ["Fills", reconcile.fill_count], ["Positions", reconcile.position_count], ["PnL", "$" + report.realized_pnl]].map(([label, value]) => `<div class="card"><div class="stat">${value}</div><div class="muted">${label}</div></div>`).join("");
      signals.innerHTML = renderSignals(signalData.signals || []);
      openTrades.innerHTML = renderOrders(tradeData.orders || []);
      positions.innerHTML = renderPositions(tradeData.positions || []);
      reportSummary.innerHTML = renderReport(report);
      events.innerHTML = renderEvents(report.events || []);
    }
    function renderSignals(items) { if (!items.length) return '<p class="muted">No signals stored yet.</p>'; return `<table><thead><tr><th>Signal</th><th>Market</th><th>Side</th><th>Edge</th><th>Notional</th></tr></thead><tbody>${items.map(s => `<tr><td><code>${s.signal_id}</code></td><td>${s.title}</td><td>${s.side}</td><td>${s.edge}</td><td>$${s.proposed_notional}</td></tr>`).join("")}</tbody></table>`; }
    function renderOrders(items) { if (!items.length) return '<p class="muted">No paper trades yet.</p>'; return `<table><thead><tr><th>Order</th><th>Market</th><th>Side</th><th>Status</th><th>Price</th><th>Size</th></tr></thead><tbody>${items.map(o => `<tr><td><code>${o.order_id}</code></td><td>${o.market_id}</td><td>${o.side}</td><td>${o.status}</td><td>${o.price}</td><td>${o.size}</td></tr>`).join("")}</tbody></table>`; }
    function renderPositions(items) { if (!items.length) return '<p class="muted">No positions yet.</p>'; return `<table><thead><tr><th>Market</th><th>Side</th><th>Size</th><th>Avg Price</th><th>Settled</th><th>Realized PnL</th></tr></thead><tbody>${items.map(p => `<tr><td>${p.market_id}</td><td>${p.side}</td><td>${p.size}</td><td>${p.average_price}</td><td>${p.settled}</td><td>${p.realized_pnl}</td></tr>`).join("")}</tbody></table>`; }
    function renderReport(r) { return `<table><tbody><tr><td>Open Exposure</td><td>$${r.open_exposure}</td></tr><tr><td>Total Cost</td><td>$${r.total_cost}</td></tr><tr><td>Realized PnL</td><td>$${r.realized_pnl}</td></tr><tr><td>Wins / Losses / Pushes</td><td>${r.wins} / ${r.losses} / ${r.pushes}</td></tr></tbody></table><p><a href="/report.html">Open printable report</a></p>`; }
    function renderEvents(items) { if (!items.length) return '<p class="muted">No events yet.</p>'; return `<table><thead><tr><th>Event</th><th>Time</th><th>Payload</th></tr></thead><tbody>${items.slice().reverse().map(e => `<tr><td><code>${e.event_type}</code></td><td>${e.created_at}</td><td><code>${JSON.stringify(e.payload)}</code></td></tr>`).join("")}</tbody></table>`; }
    async function ingestSignal() { const result = await api("/signals", { method: "POST", body: signalPayload.value }); show(result); await refresh(); }
    async function approveSignal() { const result = await api("/approvals", { method: "POST", body: approvalPayload.value }); show(result); await refresh(); }
    async function settleMarket() { const result = await api("/settlements", { method: "POST", body: settlementPayload.value }); show(result); await refresh(); }
    async function autoTrade() { const result = await api("/auto-trade", { method: "POST", body: autoTradePayload.value }); show(result); await refresh(); }
    refresh().catch(show);
    setInterval(() => refresh().catch(show), 5000);
  </script>
</body>
</html>
"""
