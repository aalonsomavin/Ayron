import React from "react";
import { Card } from "../../components/core/Card.jsx";
import { Badge } from "../../components/core/Badge.jsx";
import { Button } from "../../components/core/Button.jsx";
import { Icon } from "../../components/icons/Icon.jsx";
import { TREND_PTS, REGION_ROWS } from "./data.js";

function Metric({ label, value, delta, up }) {
  return (
    <Card padding={18}>
      <div style={{ fontSize: 13, color: "var(--ay-text-muted)" }}>{label}</div>
      <div style={{ fontFamily: "var(--ay-font-mono)", fontSize: 26, fontWeight: 600, letterSpacing: "-0.01em", marginTop: 6 }}>{value}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 4, fontSize: 13, fontWeight: 500, color: up ? "var(--ay-success-700)" : "var(--ay-danger-700)" }}>
        <Icon name={up ? "arrowup" : "arrowdown"} size={13} />{delta}
        <span style={{ color: "var(--ay-text-subtle)", fontWeight: 400 }}>vs last month</span>
      </div>
    </Card>
  );
}

function LineChart() {
  const w = 560, h = 150, max = 80;
  const path = TREND_PTS.map((p, i) => `${i ? "L" : "M"}${(i / (TREND_PTS.length - 1)) * w},${h - (p / max) * h}`).join(" ");
  const area = `${path} L${w},${h} L0,${h} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height="150" preserveAspectRatio="none">
      <defs>
        <linearGradient id="ay-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--ay-blue-500)" stopOpacity="0.16" />
          <stop offset="100%" stopColor="var(--ay-blue-500)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0, 0.5, 1].map((f) => <line key={f} x1="0" y1={h * f} x2={w} y2={h * f} stroke="var(--ay-border-subtle)" strokeWidth="1" />)}
      <path d={area} fill="url(#ay-area)" />
      <path d={path} fill="none" stroke="var(--ay-blue-500)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const PRODUCTS = [
  ["Pro plan", "3,204", "$284,200", "+14.2%", true],
  ["Team plan", "1,890", "$226,800", "+9.8%", true],
  ["Enterprise", "142", "$198,400", "+31.0%", true],
  ["Add-on: Storage", "2,410", "$48,200", "-2.4%", false],
];

/** Revenue overview dashboard. */
export function DashboardScreen() {
  return (
    <div style={{ padding: 24, overflowY: "auto", height: "100%" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 14 }}>
        <Metric label="Revenue" value="$1.28M" delta="12.4%" up />
        <Metric label="Active users" value="48,210" delta="8.1%" up />
        <Metric label="Avg. order value" value="$86.40" delta="2.3%" up />
        <Metric label="Churn rate" value="3.2%" delta="0.6%" up={false} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 14 }}>
        <Card padding={18}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600, whiteSpace: "nowrap" }}>Revenue trend</div>
              <div style={{ fontSize: 12.5, color: "var(--ay-text-muted)" }}>Last 12 months</div>
            </div>
            <Badge tone="accent">Live</Badge>
          </div>
          <LineChart />
        </Card>
        <Card padding={18}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 14, whiteSpace: "nowrap" }}>Revenue by region</div>
          {REGION_ROWS.map((r, i) => (
            <div key={r.r} style={{ marginBottom: 13 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 5 }}>
                <span style={{ fontWeight: 500, whiteSpace: "nowrap" }}>{r.r}</span>
                <span style={{ fontFamily: "var(--ay-font-mono)", color: "var(--ay-text-muted)" }}>{r.v}</span>
              </div>
              <div style={{ height: 7, borderRadius: "999px", background: "var(--ay-bg-muted)", overflow: "hidden" }}>
                <div style={{ width: `${r.pct}%`, height: "100%", borderRadius: "999px", background: `var(--ay-chart-${i + 1})` }} />
              </div>
            </div>
          ))}
        </Card>
      </div>
      <Card style={{ marginTop: 14 }} padding={0}>
        <div style={{ display: "flex", alignItems: "center", padding: "14px 18px", borderBottom: "1px solid var(--ay-border)" }}>
          <span style={{ fontSize: 15, fontWeight: 600, whiteSpace: "nowrap" }}>Top products</span>
          <span style={{ marginLeft: "auto" }}><Button size="sm" variant="ghost" leftIcon={<Icon name="filter" size={16} />}>Filter</Button></span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", padding: "9px 18px", fontSize: 11.5, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--ay-text-subtle)", fontWeight: 500, background: "var(--ay-bg-subtle)" }}>
          <span>Product</span><span style={{ textAlign: "right" }}>Units</span><span style={{ textAlign: "right" }}>Revenue</span><span style={{ textAlign: "right" }}>Δ MoM</span>
        </div>
        {PRODUCTS.map((row, i) => (
          <div key={i} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", padding: "12px 18px", fontSize: 14, borderTop: "1px solid var(--ay-border-subtle)", alignItems: "center" }}>
            <span style={{ fontWeight: 500 }}>{row[0]}</span>
            <span style={{ textAlign: "right", fontFamily: "var(--ay-font-mono)", fontSize: 13 }}>{row[1]}</span>
            <span style={{ textAlign: "right", fontFamily: "var(--ay-font-mono)", fontSize: 13 }}>{row[2]}</span>
            <span style={{ textAlign: "right", fontSize: 13, fontWeight: 500, color: row[4] ? "var(--ay-success-700)" : "var(--ay-danger-700)" }}>{row[3]}</span>
          </div>
        ))}
      </Card>
    </div>
  );
}
