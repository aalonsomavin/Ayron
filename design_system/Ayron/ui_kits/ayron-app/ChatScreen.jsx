import React, { useState, useRef, useEffect } from "react";
import { Button } from "../../components/core/Button.jsx";
import { Card } from "../../components/core/Card.jsx";
import { Avatar } from "../../components/core/Avatar.jsx";
import { Icon } from "../../components/icons/Icon.jsx";
import { ArtifactPanel, FileCard } from "./ArtifactPanel.jsx";
import { REV_BARS, REGION_ROWS, DOC_FILE, SHEET_FILE } from "./data.js";

function MiniBars() {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 96, padding: "8px 2px 0" }}>
      {REV_BARS.map((v, i) => (
        <div key={i} style={{ flex: 1, height: `${v}%`, background: i >= 10 ? "var(--ay-chart-1)" : "var(--ay-neutral-200)", borderRadius: "3px 3px 0 0" }} />
      ))}
    </div>
  );
}

function Message({ m, onPick, onOpenDoc, activeId }) {
  if (m.who === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <div style={{ maxWidth: "78%", background: "var(--ay-ink)", color: "#fff", padding: "11px 15px", borderRadius: "16px 16px 4px 16px", fontSize: 14.5, lineHeight: 1.5 }}>{m.text}</div>
      </div>
    );
  }
  return (
    <div style={{ display: "flex", gap: 12 }}>
      <Avatar agent size={30} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14.5, lineHeight: 1.55 }}>{m.text}</div>
        {m.chart && (
          <Card style={{ marginTop: 12 }} padding={16}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
              <span style={{ fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }}>Monthly revenue</span>
              <span style={{ fontFamily: "var(--ay-font-mono)", fontSize: 13, fontWeight: 600 }}>$1,284,920</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--ay-success-700)", marginBottom: 4 }}>▲ 12.4% vs April</div>
            <MiniBars />
          </Card>
        )}
        {m.table && (
          <Card style={{ marginTop: 12 }} padding={0}>
            {REGION_ROWS.map((r, i) => (
              <div key={r.r} style={{ display: "flex", alignItems: "center", padding: "11px 16px", borderTop: i ? "1px solid var(--ay-border-subtle)" : "none" }}>
                <span style={{ flex: 1, fontSize: 14, fontWeight: 500, whiteSpace: "nowrap" }}>{r.r}</span>
                <span style={{ fontFamily: "var(--ay-font-mono)", fontSize: 13, marginRight: 16 }}>{r.v}</span>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 13, fontWeight: 500, width: 64, justifyContent: "flex-end", color: r.up ? "var(--ay-success-700)" : "var(--ay-danger-700)" }}>
                  <Icon name={r.up ? "arrowup" : "arrowdown"} size={13} />{r.d}
                </span>
              </div>
            ))}
          </Card>
        )}
        {m.follow && (
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <Button size="sm" variant="secondary" leftIcon={<Icon name="zap" size={16} />} onClick={() => onPick && onPick("Set up a weekly digest")}>Create automation</Button>
            <Button size="sm" variant="ghost" leftIcon={<Icon name="table" size={16} />}>View query</Button>
          </div>
        )}
        {m.files && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 12 }}>
            {m.files.map((f) => <FileCard key={f.id} f={f} active={f.id === activeId} onOpen={onOpenDoc} />)}
          </div>
        )}
      </div>
    </div>
  );
}

const SEED = [
  { who: "user", text: "How did revenue do last month, and what drove it?" },
  { who: "agent", text: "Revenue was $1.28M in May, up 12.4% vs April — the strongest month this year. Growth was led by EMEA (+18.2%) and APAC (+22.7%).", chart: true },
  { who: "user", text: "Break it down by region." },
  { who: "agent", text: "Here's the regional split for May:", table: true },
  { who: "user", text: "Put together a full Q2 revenue report I can share with the team." },
  { who: "agent", text: "Done. I wrote up a Q2 report with the key findings and attached the underlying numbers as a spreadsheet. Open either on the right to review, edit, or download.", files: [DOC_FILE, SHEET_FILE] },
];

/** Chat with the Ayron analytics agent — with the right-side artifact panel. */
export function ChatScreen() {
  const [msgs, setMsgs] = useState(SEED);
  const [val, setVal] = useState("");
  const [thinking, setThinking] = useState(false);
  const [openDoc, setOpenDoc] = useState(DOC_FILE);
  const [expanded, setExpanded] = useState(false);
  const scroller = useRef(null);
  useEffect(() => { if (scroller.current) scroller.current.scrollTop = scroller.current.scrollHeight; }, [msgs, thinking]);

  const send = (q) => {
    const text = (q ?? val).trim();
    if (!text) return;
    setMsgs((m) => [...m, { who: "user", text }]);
    setVal("");
    setThinking(true);
    const wantsFile = /report|spreadsheet|excel|export|\bdoc\b|document|write.?up|summary/i.test(text);
    setTimeout(() => {
      setThinking(false);
      if (wantsFile) {
        setMsgs((m) => [...m, { who: "agent", text: "Here you go — I generated a written report and a spreadsheet with the supporting data. Open either on the right.", files: [DOC_FILE, SHEET_FILE] }]);
        setOpenDoc(DOC_FILE);
        setExpanded(false);
      } else {
        setMsgs((m) => [...m, { who: "agent", text: "I pulled the latest figures across your connected sources. EMEA continues to lead, and the APAC trend is accelerating — want me to set up a weekly digest for this?", follow: true }]);
      }
    }, 1100);
  };

  const suggestions = ["Generate a Q2 report", "Which products grew fastest?", "Forecast next month"];
  const mw = openDoc ? "none" : 760;
  const pad = openDoc ? "0 24px" : "0 28px";

  return (
    <div style={{ display: "flex", height: "100%" }}>
      <div style={{ flex: 1, minWidth: 0, display: expanded && openDoc ? "none" : "flex", flexDirection: "column", height: "100%", background: "var(--ay-bg)" }}>
        <div ref={scroller} style={{ flex: 1, overflowY: "auto", padding: "28px 0" }}>
          <div style={{ maxWidth: mw, margin: "0 auto", padding: pad, display: "flex", flexDirection: "column", gap: 22 }}>
            {msgs.map((m, i) => <Message key={i} m={m} onPick={send} onOpenDoc={(d) => { setOpenDoc(d); setExpanded(false); }} activeId={openDoc && openDoc.id} />)}
            {thinking && (
              <div style={{ display: "flex", gap: 12 }}>
                <Avatar agent size={30} />
                <div style={{ display: "flex", alignItems: "center", gap: 5, height: 30 }}>
                  {[0, 1, 2].map((i) => <span key={i} style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--ay-neutral-400)" }} />)}
                </div>
              </div>
            )}
          </div>
        </div>
        <div style={{ flex: "none", padding: "0 0 22px" }}>
          <div style={{ maxWidth: mw, margin: "0 auto", padding: pad }}>
            <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
              {suggestions.map((s) => (
                <button key={s} onClick={() => send(s)} style={{ height: 30, padding: "0 12px", borderRadius: "var(--ay-radius-full)", border: "1px solid var(--ay-border-strong)", background: "var(--ay-surface)", color: "var(--ay-text-muted)", fontSize: 13, fontFamily: "inherit", cursor: "pointer", boxShadow: "var(--ay-shadow-xs)" }}>{s}</button>
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 10, background: "var(--ay-surface)", border: "1px solid var(--ay-border-strong)", borderRadius: "var(--ay-radius-lg)", padding: "10px 10px 10px 14px", boxShadow: "var(--ay-shadow-sm)" }}>
              <input value={val} onChange={(e) => setVal(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") send(); }} placeholder="Ask Ayron about your data…" style={{ flex: 1, border: "none", outline: "none", background: "transparent", fontSize: 15, color: "var(--ay-text)", height: 30, fontFamily: "inherit" }} />
              <Button leftIcon={<Icon name="sparkles" size={16} />} onClick={() => send()}>Ask</Button>
            </div>
            <div style={{ textAlign: "center", fontSize: 12, color: "var(--ay-text-subtle)", marginTop: 10 }}>Ayron queries your connected sources. Always verify critical figures.</div>
          </div>
        </div>
      </div>
      {openDoc && <ArtifactPanel doc={openDoc} expanded={expanded} onToggleExpand={() => setExpanded((e) => !e)} onClose={() => { setOpenDoc(null); setExpanded(false); }} />}
    </div>
  );
}
