import React, { useState } from "react";
import { Button } from "../../components/core/Button.jsx";
import { Avatar } from "../../components/core/Avatar.jsx";
import { Icon } from "../../components/icons/Icon.jsx";
import { ChatScreen } from "./ChatScreen.jsx";
import { DashboardScreen } from "./DashboardScreen.jsx";
import { SourcesScreen } from "./SourcesScreen.jsx";
import { AutomationsScreen } from "./AutomationsScreen.jsx";

const NAV = [
  ["chat", "Chat", "message"],
  ["dashboard", "Dashboard", "dashboard"],
  ["sources", "Sources", "database"],
  ["automations", "Automations", "zap"],
];
const TITLES = {
  chat: ["Chat", "Ask Ayron anything about your data"],
  dashboard: ["Dashboard", "Revenue overview · updated 3 min ago"],
  sources: ["Sources", "Manage your connected data sources"],
  automations: ["Automations", "Scheduled workflows and alerts"],
};
const SCREENS = { chat: ChatScreen, dashboard: DashboardScreen, sources: SourcesScreen, automations: AutomationsScreen };

function Sidebar({ active, setActive }) {
  return (
    <aside style={{ width: 256, flex: "none", background: "var(--ay-bg)", borderRight: "1px solid var(--ay-border)", display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "18px 18px 14px", display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ width: 28, height: 28, borderRadius: 8, background: "var(--ay-ink)", display: "inline-flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: 16, letterSpacing: "-0.04em" }}>A</span>
        <span style={{ fontSize: 17, fontWeight: 600, letterSpacing: "-0.03em" }}>Ayron</span>
        <span style={{ marginLeft: "auto", color: "var(--ay-text-subtle)" }}><Icon name="chevdown" size={16} /></span>
      </div>
      <div style={{ padding: "4px 12px 0" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, height: 34, padding: "0 10px", borderRadius: "var(--ay-radius-md)", border: "1px solid var(--ay-border)", color: "var(--ay-text-subtle)", fontSize: 13, background: "var(--ay-bg-subtle)" }}>
          <Icon name="search" size={15} /><span>Search</span>
          <span style={{ marginLeft: "auto", fontFamily: "var(--ay-font-mono)", fontSize: 11, opacity: 0.8 }}>⌘K</span>
        </div>
      </div>
      <nav style={{ padding: "12px 12px", display: "flex", flexDirection: "column", gap: 2 }}>
        {NAV.map(([k, label, ic]) => {
          const on = active === k;
          return (
            <button key={k} onClick={() => setActive(k)} style={{ display: "flex", alignItems: "center", gap: 10, height: 36, padding: "0 10px", border: "none", borderRadius: "var(--ay-radius-md)", cursor: "pointer", fontSize: 14, fontWeight: on ? 600 : 500, fontFamily: "inherit", color: on ? "var(--ay-text)" : "var(--ay-text-muted)", background: on ? "var(--ay-surface-hover)" : "transparent", textAlign: "left" }}>
              <Icon name={ic} size={17} stroke={on ? 2.2 : 1.9} />{label}
            </button>
          );
        })}
      </nav>
      <div style={{ marginTop: "auto", padding: 12, borderTop: "1px solid var(--ay-border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 8px" }}>
          <Avatar name="Dana Lee" status="online" size={30} />
          <div style={{ lineHeight: 1.2 }}>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Dana Lee</div>
            <div style={{ fontSize: 12, color: "var(--ay-text-subtle)" }}>Acme Analytics</div>
          </div>
          <span style={{ marginLeft: "auto", color: "var(--ay-text-subtle)" }}><Icon name="settings" size={16} /></span>
        </div>
      </div>
    </aside>
  );
}

/**
 * Full Ayron product shell — sidebar + top bar + the four core screens.
 * @startingPoint section="Ayron App" subtitle="Full app shell — chat, dashboard, sources, automations" viewport="1280x800"
 */
export function AppShell() {
  const [active, setActive] = useState("chat");
  const action = {
    chat: <Button variant="secondary" size="sm" leftIcon={<Icon name="plus" size={16} />}>New chat</Button>,
    dashboard: (
      <>
        <Button variant="ghost" size="sm" leftIcon={<Icon name="refresh" size={16} />}>Refresh</Button>
        <Button size="sm" leftIcon={<Icon name="arrowdown" size={16} />}>Export</Button>
      </>
    ),
    sources: <Button size="sm" leftIcon={<Icon name="plus" size={16} />}>Connect a source</Button>,
    automations: <Button size="sm" leftIcon={<Icon name="plus" size={16} />}>New automation</Button>,
  }[active];
  const Screen = SCREENS[active];
  const [title, sub] = TITLES[active];

  return (
    <div style={{ display: "flex", height: "100%", minHeight: 720, background: "var(--ay-bg-subtle)", fontFamily: "var(--ay-font-sans)", color: "var(--ay-text)" }}>
      <Sidebar active={active} setActive={setActive} />
      <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", height: "100%", background: active === "chat" ? "var(--ay-bg)" : "var(--ay-bg-subtle)" }}>
        <header style={{ height: 60, flex: "none", borderBottom: "1px solid var(--ay-border)", background: "var(--ay-bg)", display: "flex", alignItems: "center", gap: 14, padding: "0 24px" }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 16, fontWeight: 600, letterSpacing: "-0.01em", whiteSpace: "nowrap" }}>{title}</div>
            <div style={{ fontSize: 12.5, color: "var(--ay-text-muted)", whiteSpace: "nowrap" }}>{sub}</div>
          </div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>{action}</div>
        </header>
        <div style={{ flex: 1, minHeight: 0 }}><Screen /></div>
      </main>
    </div>
  );
}
