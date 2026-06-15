# Ayron — Product UI Kit

A high-fidelity, click-through recreation of the Ayron analytics app. Light mode,
dev-tool aesthetic, built entirely on the design system's tokens and core
components.

## What's here
- **`index.html`** — self-contained interactive app (React + Babel from CDN).
  Open it directly: navigate the sidebar between the four screens, send a chat
  message to the agent, toggle automations on/off. This is the canonical preview
  and the file the Design System tab renders.
- **Modular source** (composes `components/core/*` + `components/icons/Icon`):
  - `AppShell.jsx` — sidebar + top bar + screen router (marked as a starting point).
  - `ChatScreen.jsx` — conversation with the analytics agent (messages, inline
    chart/table answers, suggested follow-ups, composer, "thinking" state, and
    **agent-generated file artifacts**).
  - `ArtifactPanel.jsx` — right-side split-pane viewer (like Claude's). When the
    agent generates a report it posts file cards in the chat; clicking one opens
    it on the right as a formatted **document** (`DocView`) or an Excel-style
    **spreadsheet** (`SheetView`) with copy / download / expand / close actions.
    Asking the agent for a "report" / "spreadsheet" generates new artifacts.
  - `DashboardScreen.jsx` — KPI metrics, revenue line chart, region bars, top-products table.
  - `SourcesScreen.jsx` — connected sources list with status, plus integration catalog.
  - `AutomationsScreen.jsx` — workflow cards with live on/off switches.
  - `data.js` — sample data for all screens.

## Notes
- Charts are lightweight SVG/CSS (line, bars, progress) using the data-viz tokens
  (`--ay-chart-*`). They're illustrative, not a charting library.
- Source/integration tiles use a generic database glyph as a placeholder — swap in
  real brand marks (Postgres, Snowflake, Stripe, …) for production.
- The agent's replies are canned; wire `ChatScreen`'s `send()` to a real backend.
