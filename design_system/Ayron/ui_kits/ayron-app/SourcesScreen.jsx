import React from "react";
import { Card } from "../../components/core/Card.jsx";
import { Badge } from "../../components/core/Badge.jsx";
import { Icon } from "../../components/icons/Icon.jsx";
import { SOURCES, AVAILABLE } from "./data.js";

const STATUS = { connected: ["success", "Connected"], syncing: ["warning", "Syncing"], error: ["danger", "Error"] };

function SourceLogo({ s, size = 36 }) {
  return (
    <span style={{ width: size, height: size, borderRadius: "var(--ay-radius-md)", flex: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", background: s.color + "14", color: s.color, border: `1px solid ${s.color}28` }}>
      <Icon name="database" size={18} />
    </span>
  );
}

/** Connected data sources + integration catalog. */
export function SourcesScreen() {
  return (
    <div style={{ padding: 24, overflowY: "auto", height: "100%" }}>
      <Card style={{ marginBottom: 24 }} padding={0}>
        <div style={{ display: "flex", alignItems: "center", padding: "14px 18px", borderBottom: "1px solid var(--ay-border)" }}>
          <span style={{ fontSize: 15, fontWeight: 600, whiteSpace: "nowrap" }}>Connected sources</span>
          <Badge tone="neutral" style={{ marginLeft: 8 }}>{SOURCES.length}</Badge>
        </div>
        {SOURCES.map((s, i) => {
          const [tone, label] = STATUS[s.status];
          return (
            <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 18px", borderTop: i ? "1px solid var(--ay-border-subtle)" : "none" }}>
              <SourceLogo s={s} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.name}</div>
                <div style={{ fontSize: 12.5, color: "var(--ay-text-muted)", whiteSpace: "nowrap" }}>{s.type} · {s.rows} rows</div>
              </div>
              <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 18 }}>
                <span style={{ fontSize: 12.5, color: "var(--ay-text-subtle)", fontFamily: "var(--ay-font-mono)" }}>{s.sync}</span>
                <Badge tone={tone} dot>{label}</Badge>
                <span style={{ color: "var(--ay-text-subtle)", cursor: "pointer" }}><Icon name="dots" size={18} /></span>
              </div>
            </div>
          );
        })}
      </Card>

      <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>Add a source</div>
      <div style={{ fontSize: 13, color: "var(--ay-text-muted)", marginBottom: 14 }}>Connect a database, warehouse, or SaaS tool. Ayron handles the schema.</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 }}>
        {AVAILABLE.map((n) => (
          <Card key={n} interactive style={{ padding: 14, display: "flex", alignItems: "center", gap: 11, cursor: "pointer" }}>
            <span style={{ width: 30, height: 30, borderRadius: 8, background: "var(--ay-bg-muted)", display: "inline-flex", alignItems: "center", justifyContent: "center", color: "var(--ay-text-muted)", flex: "none" }}>
              <Icon name="database" size={16} />
            </span>
            <span style={{ fontSize: 13.5, fontWeight: 500 }}>{n}</span>
            <span style={{ marginLeft: "auto", color: "var(--ay-text-subtle)" }}><Icon name="plus" size={16} /></span>
          </Card>
        ))}
      </div>
    </div>
  );
}
