# Ayron Design System

**Ayron** is an AI agent for data analytics. Companies connect data sources from
anywhere, chat with an analytics AI agent to explore and answer questions, build
charts and dashboards, and create automations / workflows on top of their data.

This design system defines Ayron's visual identity, foundations, reusable
components, and product UI kit. The aesthetic is a **clean, technical, dev-tool**
look — light mode, near-monochrome ink palette, geometric grotesque type
(Geist), generous whitespace, hairline borders, and very soft shadows. Color is
used sparingly and intentionally: a single restrained blue for focus / selection
/ primary data series, plus a small categorical palette for charts.

> Reference direction: Cursor (light mode) — geometric sans, solid near-black
> buttons, monochrome surfaces. Ayron's identity is **original** and inspired by
> that genre, not a copy of any brand's proprietary assets.

## Sources & status
- Brand/logo: **placeholder**. A wordmark set in Geist + a geometric symbol mark
  live in `assets/logo/`. The user will supply final brand assets — swap them in.
- Fonts: **Geist** + **Geist Mono**, loaded from Google Fonts (`tokens/fonts.css`).
  If you need self-hosted binaries, drop them in `assets/fonts/` and replace the
  `@import` with `@font-face`.
- Theme: **light mode only** (per brief). Color tokens are structured so a dark
  scope could be added later, but no dark theme ships today.

---

## CONTENT FUNDAMENTALS — how Ayron writes

**Voice:** confident, precise, and quietly technical. Ayron talks like a sharp
data colleague, not a hype machine. It states what it did and what it found.

- **Tone:** plain, direct, low-adjective. Prefer "Connected Postgres" over
  "Successfully established a connection to your database!". Never exclamatory.
- **Person:** address the user as **you**; the agent refers to itself sparingly
  ("I pulled the last 90 days"). Avoid "we" for the product.
- **Casing:** sentence case everywhere — buttons, headers, menus, titles.
  ("Connect a source", not "Connect A Source" or "CONNECT A SOURCE.")
- **Numbers & data:** always concrete. Show the metric, the delta, and the time
  window. Use tabular/mono figures for anything numeric.
- **Verbs:** lead with the action — Connect, Ask, Build, Automate, Run, Sync.
- **Emoji:** none in product UI. (Source/integration logos are real brand icons,
  not emoji.)
- **Errors:** human and actionable — say what happened and the next step.
  ("Couldn't reach the warehouse. Check credentials and retry.")
- **Empty states:** invite the first action, no fluff. ("No sources yet.
  Connect one to start asking questions.")

Example copy:
- Hero: "Ask your data anything."
- Sub: "Connect your sources and let Ayron query, chart, and automate."
- Button: "Connect a source" / "Ask Ayron" / "New automation"
- Agent line: "Revenue is up 12.4% vs. last month, driven by EMEA. Want a chart?"

---

## VISUAL FOUNDATIONS

**Color.** Near-monochrome. Surfaces are white (`--ay-bg`) and faint gray
(`--ay-bg-subtle` / `--ay-bg-muted`). Text is near-black ink. **Primary actions
are ink/near-black** (`--ay-primary`) with white text — the "accent" is
essentially black, like Cursor. A single **brand blue** (`--ay-accent`,
`#3b6ef6`) is reserved for focus rings, selected/active states, links, and the
primary chart series — never for large fills. Semantic colors (success/warning/
danger/info) appear only in status contexts. Charts use the 8-color categorical
palette (`--ay-chart-1..8`).

**Type.** Geist for all UI; Geist Mono for data, metrics, SQL, and code.
Display/headings track tight (`-0.02em`) and use weight 600–700. Body is 15px /
1.5 at weight 400. Numeric data uses mono with tabular feel. No serif.

**Spacing.** 4px base grid (`--ay-space-*`). Components breathe — comfortable
padding, clear grouping. App chrome: 256px sidebar, 1200px content container.

**Backgrounds.** Flat. White or faint gray. **No gradients** on surfaces, **no
hero illustrations, no photography, no textures.** Depth comes from hairline
borders and soft shadows, not color. A barely-there dotted/grid texture is
acceptable only behind empty canvases (e.g. an empty dashboard).

**Borders.** 1px hairlines (`--ay-border`, `#e6e6e8`) carry most of the
separation. Cards, inputs, menus, table rows — all delineated by borders first,
shadow second.

**Shadows.** Very soft and low-contrast (`--ay-shadow-xs..lg`). Resting cards
often use *only* a border (no shadow); shadows are for lifted/floating layers
(menus, popovers, dialogs, dragging).

**Radii.** ~8px base (`--ay-radius-md`). Inputs/buttons 6–8px, cards 12px,
pills/avatars full. Nothing sharp, nothing bubbly.

**Motion.** Quick and restrained. 120–180ms with `--ay-ease`. Fades and small
translates (4–8px). No bounce, no spring, no long flourishes. Spinners and
shimmer for loading; the agent "thinking" state is a subtle pulsing caret/dots.

**Interactive states.**
- *Hover:* surfaces step one neutral darker (`--ay-surface-hover`); primary
  buttons go to `--ay-primary-hover` (pure black); ghost items get a faint gray
  fill.
- *Press:* slightly darker, no scale (or a tiny 0.99 on big targets).
- *Focus:* 3px blue ring (`--ay-shadow-focus`) + border to blue. Always visible.
- *Selected:* faint blue tint background (`--ay-selection-bg`) + blue left marker
  or border.
- *Disabled:* `--ay-text-disabled`, reduced contrast, no shadow.

**Cards.** White, `--ay-radius-lg`, 1px border, optional `--ay-shadow-sm`.
Headers use h3/h4 in semibold; supporting text in `--ay-text-muted`.

---

## ICONOGRAPHY

- **System:** [Lucide](https://lucide.dev) — thin, geometric, 1.5–2px stroke,
  rounded joints. It matches the technical/dev-tool feel and pairs well with
  Geist. Loaded from CDN in the UI kits (`lucide` web font / SVG). **Substitution
  flag:** Ayron has no proprietary icon set yet, so Lucide is the chosen
  stand-in. If a branded set arrives, swap it project-wide.
- **Size:** 16px in dense UI, 18–20px in nav/buttons, stroke ~1.75.
- **Color:** inherit text color; muted icons use `--ay-text-muted`.
- **Source/integration logos** (Postgres, Snowflake, BigQuery, Stripe, GA4, …)
  are real brand marks rendered as small monochrome or full-color tiles — never
  redrawn or replaced with emoji.
- **Emoji / unicode as icons:** never.

---

## INDEX — what's in this system

- `styles.css` — global entry point (consumers link this). `@import`s only.
- `tokens/` — `fonts.css`, `colors.css`, `typography.css`, `spacing.css`,
  `effects.css`.
- `assets/logo/` — placeholder symbol marks (ink + light).
- `components/` — reusable React primitives (Button, Input, Badge, Card, Tabs,
  Switch, Avatar). Each has `.jsx`, `.d.ts`, `.prompt.md`, and a `*.card.html`.
- `ui_kits/ayron-app/` — product UI kit: chat with the agent, dashboard, data
  sources, automations. `index.html` is an interactive click-through.
- `guidelines/` — foundation specimen cards (Type, Colors, Spacing, Effects)
  shown in the Design System tab.
- `SKILL.md` — Agent-Skill manifest for downloading/using this system elsewhere.
