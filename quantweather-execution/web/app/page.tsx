"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

type Signal = {
  signal_id: string;
  market_id: string;
  title: string;
  side: "YES" | "NO";
  edge: number;
  confidence: number;
  proposed_notional: number;
  source_run_id: string;
  expires_at?: string;
};

type Order = {
  order_id: string;
  market_id: string;
  side: "YES" | "NO";
  status: string;
  price: number;
  size: number;
};

type Position = {
  market_id: string;
  side: "YES" | "NO";
  size: number;
  average_price: number;
  realized_pnl: number;
  settled: boolean;
};

type EventRecord = {
  event_type: string;
  created_at: string;
  payload: Record<string, unknown>;
};

type DashboardState = {
  health: { status: string };
  reconcile: {
    approval_count: number;
    intent_count: number;
    order_count: number;
    fill_count: number;
    position_count: number;
    event_count: number;
    healthy: boolean;
  };
  signals: { signals: Signal[] };
  trades: {
    orders: Order[];
    positions: Position[];
    open_positions: Position[];
    settled_positions: Position[];
  };
  report: {
    order_count: number;
    fill_count: number;
    open_position_count: number;
    settled_position_count: number;
    open_exposure: number;
    total_cost: number;
    realized_pnl: number;
    wins: number;
    losses: number;
    pushes: number;
    events: EventRecord[];
  };
};

const sampleSignal = {
  signal_id: "sig-ui-1",
  market_id: "mkt-ui-1",
  title: "NYC high at or above 80F?",
  side: "YES",
  edge: 0.12,
  confidence: 0.75,
  proposed_notional: 100,
  source_run_id: "run-ui-1",
  expires_at: "2026-04-27T23:59:59Z",
  created_at: "2026-04-20T18:30:00Z"
};

const sampleApproval = {
  signal_id: "sig-ui-1",
  decision: {
    signal_id: "sig-ui-1",
    status: "approved",
    decided_at: "2026-04-20T18:31:00Z",
    actor: "eric",
    rationale: "looks good"
  },
  risk_limits: { max_order_notional: 500 },
  created_at: "2026-04-20T18:31:00Z",
  intent_id: "intent-ui-1",
  order_id: "order-ui-1",
  fill_id: "fill-ui-1"
};

const sampleAutoTrade = {
  created_at: "2026-04-20T18:35:00Z",
  min_edge: 0.05,
  min_confidence: 0.45,
  max_notional: 250,
  max_order_notional: 500,
  actor: "auto-paper-trader"
};

const sampleSettlement = {
  market_id: "mkt-ui-1",
  winning_side: "YES",
  created_at: "2026-04-20T19:00:00Z"
};

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/execution-api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}${detail ? `: ${detail.slice(0, 160)}` : ""}`);
  }
  return response.json() as Promise<T>;
}

function money(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardState | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [error, setError] = useState("");
  const [lastResponse, setLastResponse] = useState("Ready.");
  const [signalPayload, setSignalPayload] = useState(JSON.stringify(sampleSignal, null, 2));
  const [approvalPayload, setApprovalPayload] = useState(JSON.stringify(sampleApproval, null, 2));
  const [autoPayload, setAutoPayload] = useState(JSON.stringify(sampleAutoTrade, null, 2));
  const [settlementPayload, setSettlementPayload] = useState(JSON.stringify(sampleSettlement, null, 2));
  const [isPending, startTransition] = useTransition();

  async function refresh() {
    const [health, reconcile, signals, trades, report] = await Promise.all([
      getJson<DashboardState["health"]>("/health"),
      getJson<DashboardState["reconcile"]>("/reconcile"),
      getJson<DashboardState["signals"]>("/signals"),
      getJson<DashboardState["trades"]>("/trades"),
      getJson<DashboardState["report"]>("/report")
    ]);

    startTransition(() => {
      setData({ health, reconcile, signals, trades, report });
      setError("");
    });
  }

  useEffect(() => {
    refresh().catch((err: unknown) => setError(String(err)));
    const id = window.setInterval(() => {
      refresh().catch((err: unknown) => setError(String(err)));
    }, 5000);
    return () => window.clearInterval(id);
  }, []);

  const safeData: DashboardState = data ?? {
    health: { status: "offline" },
    reconcile: {
      approval_count: 0,
      intent_count: 0,
      order_count: 0,
      fill_count: 0,
      position_count: 0,
      event_count: 0,
      healthy: false
    },
    signals: { signals: [] },
    trades: { orders: [], positions: [], open_positions: [], settled_positions: [] },
    report: {
      order_count: 0,
      fill_count: 0,
      open_position_count: 0,
      settled_position_count: 0,
      open_exposure: 0,
      total_cost: 0,
      realized_pnl: 0,
      wins: 0,
      losses: 0,
      pushes: 0,
      events: []
    }
  };

  const netTone = useMemo(() => {
    if (!data) return "neutral";
    if (safeData.report.realized_pnl > 0) return "positive";
    if (safeData.report.realized_pnl < 0) return "negative";
    return "neutral";
  }, [data, safeData.report.realized_pnl]);

  async function post(path: string, payload: string) {
    const result = await getJson(path, { method: "POST", body: payload });
    setLastResponse(JSON.stringify(result, null, 2));
    await refresh();
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">QuantWeather Execution</p>
          <h1>Paper trading cockpit</h1>
          <p className="lede">
            Monitor signals, paper trades, outcomes, and automation rules from a real dashboard.
          </p>
        </div>
        <div className={`status ${safeData.reconcile.healthy ? "online" : "warning"}`}>
          <span>{safeData.health.status}</span>
          <small>{isPending ? "refreshing" : data ? "live refresh" : "backend offline"}</small>
        </div>
      </section>

      <section className="utility-bar">
        <button onClick={() => post("/cleanup-duplicates", "{}")}>Clean duplicate local rows</button>
        <span>Use this if old repeated test/manual submissions polluted the local SQLite database.</span>
      </section>

      {error && (
        <div className="alert">
          Backend unavailable. Start it with <code>env PYTHONPATH=src python3 -m quantweather_execution.api --host 127.0.0.1 --port 8080</code>
          <br />
          <small>{error}</small>
        </div>
      )}

      <section className="metric-grid">
        <Metric label="Open exposure" value={money(safeData.report.open_exposure)} />
        <Metric label="Realized PnL" value={money(safeData.report.realized_pnl)} tone={netTone} />
        <Metric label="Open positions" value={String(safeData.report.open_position_count)} />
        <Metric label="Wins / Losses" value={`${safeData.report.wins}/${safeData.report.losses}`} />
        <Metric label="Orders" value={String(safeData.report.order_count)} />
        <Metric label="Signals" value={String(safeData.signals.signals.length)} />
      </section>

      <section className="dashboard-grid">
        <Panel title="Signals" subtitle="Candidate trades waiting for approval or automation">
          <SignalsTable signals={safeData.signals.signals} />
        </Panel>
        <Panel title="Open trades" subtitle="Every filled paper order appears here">
          <OrdersTable orders={safeData.trades.orders} />
        </Panel>
        <Panel title="Positions & outcomes" subtitle="Settle outcomes to see realized paper PnL">
          <PositionsTable positions={safeData.trades.positions} onSelect={setSelectedPosition} />
        </Panel>
        <Panel title="Recent events" subtitle="Audit trail">
          <Events events={safeData.report.events} />
        </Panel>
      </section>

      <section className="actions-grid">
        <ActionCard
          title="Ingest signal"
          button="Store signal"
          value={signalPayload}
          onChange={setSignalPayload}
          onSubmit={() => post("/signals", signalPayload)}
        />
        <ActionCard
          title="Manual approval"
          button="Approve + paper trade"
          value={approvalPayload}
          onChange={setApprovalPayload}
          onSubmit={() => post("/approvals", approvalPayload)}
          accent
        />
        <ActionCard
          title="Auto paper-trade rules"
          button="Evaluate rules"
          value={autoPayload}
          onChange={setAutoPayload}
          onSubmit={() => post("/auto-trade", autoPayload)}
        />
        <ActionCard
          title="Settle outcome"
          button="Settle market"
          value={settlementPayload}
          onChange={setSettlementPayload}
          onSubmit={() => post("/settlements", settlementPayload)}
          danger
        />
      </section>

      <Panel title="Latest API response" subtitle="Useful while wiring automations">
        <pre className="response">{lastResponse}</pre>
      </Panel>

      {selectedPosition && (
        <PositionModal
          position={selectedPosition}
          signals={safeData.signals.signals}
          orders={safeData.trades.orders}
          events={safeData.report.events}
          onClose={() => setSelectedPosition(null)}
        />
      )}
    </main>
  );
}

function Metric({ label, value, tone = "neutral" }: { label: string; value: string; tone?: string }) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Panel({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function SignalsTable({ signals }: { signals: Signal[] }) {
  if (!signals.length) return <Empty text="No stored signals yet." />;
  return (
    <table>
      <thead>
        <tr><th>Signal</th><th>Market</th><th>Side</th><th>Edge</th><th>Notional</th></tr>
      </thead>
      <tbody>
        {signals.map((signal) => (
          <tr key={signal.signal_id}>
            <td><code>{signal.signal_id}</code></td>
            <td>{signal.title}</td>
            <td><Badge>{signal.side}</Badge></td>
            <td>{signal.edge}</td>
            <td>{money(signal.proposed_notional)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function OrdersTable({ orders }: { orders: Order[] }) {
  if (!orders.length) return <Empty text="No paper trades yet." />;
  return (
    <table>
      <thead>
        <tr><th>Order</th><th>Market</th><th>Side</th><th>Status</th><th>Price</th><th>Size</th></tr>
      </thead>
      <tbody>
        {orders.map((order, index) => (
          <tr key={`${order.order_id}-${index}`}>
            <td><code>{order.order_id}</code></td>
            <td>{order.market_id}</td>
            <td><Badge>{order.side}</Badge></td>
            <td>{order.status}</td>
            <td>{order.price}</td>
            <td>{money(order.size)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PositionsTable({ positions, onSelect }: { positions: Position[]; onSelect: (position: Position) => void }) {
  if (!positions.length) return <Empty text="No positions yet." />;
  return (
    <table>
      <thead>
        <tr><th>Market</th><th>Position</th><th>Size</th><th>Avg</th><th>Status</th><th>PnL</th><th>Details</th></tr>
      </thead>
      <tbody>
        {positions.map((position) => (
          <tr key={`${position.market_id}-${position.side}`}>
            <td>{position.market_id}</td>
            <td><Badge>{sideLabel(position.side)}</Badge></td>
            <td>{money(position.size)}</td>
            <td>{position.average_price}</td>
            <td><Badge tone={position.settled ? "green" : "amber"}>{position.settled ? "settled" : "open"}</Badge></td>
            <td className={position.realized_pnl >= 0 ? "gain" : "loss"}>{money(position.realized_pnl)}</td>
            <td><button className="table-action" onClick={() => onSelect(position)}>View</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PositionModal({
  position,
  signals,
  orders,
  events,
  onClose
}: {
  position: Position;
  signals: Signal[];
  orders: Order[];
  events: EventRecord[];
  onClose: () => void;
}) {
  const relatedSignals = signals.filter((signal) => signal.market_id === position.market_id);
  const relatedOrders = orders.filter((order) => order.market_id === position.market_id && order.side === position.side);
  const relatedEvents = events.filter((event) => JSON.stringify(event.payload).includes(position.market_id));
  const expiration = relatedSignals.find((signal) => signal.expires_at)?.expires_at ?? "Not captured yet";

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <div>
            <p className="eyebrow">Position details</p>
            <h2>{position.market_id}</h2>
            <p className="muted">{sideLabel(position.side)} means you bought the {position.side} outcome. It pays if the market resolves {position.side}.</p>
          </div>
          <button className="close-button" onClick={onClose}>Close</button>
        </div>

        <div className="detail-grid">
          <Detail label="Position" value={sideLabel(position.side)} />
          <Detail label="Expiration" value={expiration} />
          <Detail label="Size" value={money(position.size)} />
          <Detail label="Average price" value={String(position.average_price)} />
          <Detail label="Status" value={position.settled ? "Settled" : "Open"} />
          <Detail label="Realized P/L" value={money(position.realized_pnl)} tone={position.realized_pnl >= 0 ? "gain" : "loss"} />
        </div>

        <h3>Source signals</h3>
        {relatedSignals.length ? (
          <table>
            <thead><tr><th>Signal</th><th>Title</th><th>Edge</th><th>Confidence</th><th>Run</th></tr></thead>
            <tbody>
              {relatedSignals.map((signal) => (
                <tr key={signal.signal_id}>
                  <td><code>{signal.signal_id}</code></td>
                  <td>{signal.title}</td>
                  <td>{signal.edge}</td>
                  <td>{signal.confidence}</td>
                  <td><code>{signal.source_run_id}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <Empty text="No matching source signal found in the current store." />}

        <h3>Order history</h3>
        {relatedOrders.length ? (
          <table>
            <thead><tr><th>Order</th><th>Status</th><th>Price</th><th>Size</th></tr></thead>
            <tbody>
              {relatedOrders.map((order, index) => (
                <tr key={`${order.order_id}-${index}`}>
                  <td><code>{order.order_id}</code></td>
                  <td>{order.status}</td>
                  <td>{order.price}</td>
                  <td>{money(order.size)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <Empty text="No matching orders found." />}

        <h3>Related events</h3>
        <Events events={relatedEvents} />
      </section>
    </div>
  );
}

function Detail({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="detail-card">
      <span>{label}</span>
      <strong className={tone}>{value}</strong>
    </div>
  );
}

function sideLabel(side: "YES" | "NO") {
  return side === "YES" ? "Long YES" : "Long NO";
}

function Events({ events }: { events: EventRecord[] }) {
  if (!events.length) return <Empty text="No events yet." />;
  return (
    <div className="events">
      {events.slice().reverse().map((event, index) => (
        <div className="event" key={`${event.event_type}-${index}`}>
          <code>{event.event_type}</code>
          <span>{event.created_at}</span>
          <small>{JSON.stringify(event.payload)}</small>
        </div>
      ))}
    </div>
  );
}

function ActionCard({
  title,
  button,
  value,
  onChange,
  onSubmit,
  accent = false,
  danger = false
}: {
  title: string;
  button: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  accent?: boolean;
  danger?: boolean;
}) {
  return (
    <section className="action-card">
      <h3>{title}</h3>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} />
      <button className={danger ? "danger" : accent ? "accent" : ""} onClick={onSubmit}>{button}</button>
    </section>
  );
}

function Badge({ children, tone = "blue" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}
