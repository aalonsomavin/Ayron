import React, { useState } from "react";
import { Card } from "../../components/core/Card.jsx";
import { Badge } from "../../components/core/Badge.jsx";
import { Switch } from "../../components/core/Switch.jsx";
import { Icon } from "../../components/icons/Icon.jsx";
import { AUTOMATIONS } from "./data.js";

/** Scheduled workflows and alerts. */
export function AutomationsScreen() {
  const [items, setItems] = useState(AUTOMATIONS);
  const toggle = (i) => setItems((it) => it.map((a, j) => (j === i ? { ...a, on: !a.on } : a)));

  return (
    <div style={{ padding: 24, overflowY: "auto", height: "100%" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map((a, i) => (
          <Card key={a.name} style={{ padding: "16px 18px" }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
              <span style={{ width: 38, height: 38, borderRadius: "var(--ay-radius-md)", flex: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", background: a.on ? "var(--ay-blue-50)" : "var(--ay-bg-muted)", color: a.on ? "var(--ay-blue-600)" : "var(--ay-text-subtle)" }}>
                <Icon name="zap" size={18} />
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14.5, fontWeight: 600, whiteSpace: "nowrap" }}>{a.name}</span>
                  <Badge tone="neutral">{a.channel}</Badge>
                </div>
                <div style={{ fontSize: 13, color: "var(--ay-text-muted)", marginTop: 3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{a.desc}</div>
                <div style={{ display: "flex", gap: 16, marginTop: 9, fontSize: 12.5, color: "var(--ay-text-subtle)" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><Icon name="clock" size={13} />{a.schedule}</span>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><Icon name="check" size={13} />Last run {a.last}</span>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 14, flex: "none" }}>
                <span style={{ fontSize: 12.5, color: a.on ? "var(--ay-success-700)" : "var(--ay-text-subtle)", fontWeight: 500, width: 46 }}>{a.on ? "Active" : "Paused"}</span>
                <Switch checked={a.on} onChange={() => toggle(i)} />
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
