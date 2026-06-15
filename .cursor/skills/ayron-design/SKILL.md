---
name: ayron-design
description: Design and build Ayron product UI using the Ayron design system — tokens, React components, copy voice, and product UI kit. Use when building or styling frontends, creating mocks/prototypes, designing screens, or when the user mentions Ayron branding, design system, UI kit, or product interface work. Takes precedence over generic UI libraries (e.g. daisyUI) for Ayron product code.
---

# Ayron Design System

Ayron is an AI agent for data analytics. All product UI in this repo follows the design system at `design_system/Ayron/`.

**Read first:** [design_system/Ayron/readme.md](../../../design_system/Ayron/readme.md) — full voice, foundations, and file index.

## Workflow

1. **Before writing UI**, read `design_system/Ayron/readme.md` and skim relevant source files (tokens, components, UI kit screens).
2. **Link tokens once** — import or `<link>` `design_system/Ayron/styles.css`. Use `--ay-*` CSS custom properties only; never hard-code hex values.
3. **Reuse components** — copy or import from `design_system/Ayron/components/core/` and `components/icons/`. Read each component's `.prompt.md` before use. Do not re-implement Button, Card, Input, etc.
4. **Match product patterns** — study `design_system/Ayron/ui_kits/ayron-app/` (chat, dashboard, sources, automations). `index.html` is the canonical interactive preview.
5. **Prototypes / mocks** — copy assets out and create static HTML the user can open. For production code, wire components into the app stack.

## Non-negotiables

- Light mode only. Near-monochrome surfaces (`--ay-bg`, `--ay-bg-subtle`).
- Primary actions: ink/near-black (`--ay-primary`) with white text — one `primary` button per view.
- One restrained blue (`--ay-accent`) for focus, selection, links, primary chart series — never large fills.
- Geist for UI, Geist Mono for metrics/code/SQL. Sentence case everywhere. No emoji in product UI.
- Hairline borders (`--ay-border`) do most separation; soft shadows only on floating layers.
- Radii ~8px (`--ay-radius-md`). Motion 120–180ms (`--ay-dur-fast`, `--ay-dur-normal`).
- Copy: plain, direct, lead with a verb. Address the user as "you". Concrete numbers with delta + time window in mono.

## Source map

| Path | Purpose |
|------|---------|
| `design_system/Ayron/styles.css` | Single entry — tokens + fonts |
| `design_system/Ayron/tokens/` | `--ay-*` colors, type, spacing, effects |
| `design_system/Ayron/components/core/` | Button, Input, Badge, Card, Tabs, Switch, Avatar |
| `design_system/Ayron/components/icons/` | Lucide-based `Icon` component |
| `design_system/Ayron/ui_kits/ayron-app/` | Product screens + `AppShell` |
| `design_system/Ayron/guidelines/` | Foundation specimen cards |
| `design_system/Ayron/assets/logo/` | Placeholder brand marks |

## Integration

**CSS / HTML:**
```html
<link rel="stylesheet" href="/path/to/design_system/Ayron/styles.css" />
```

**React:** copy components into the app or import relatively; style with inline `var(--ay-*)` like the core components do.

**Icons:** use `Icon` from `components/icons/Icon.jsx` (Lucide-based). 16px dense UI, 18–20px nav/buttons.

## Additional resources

- Token & component quick reference: [reference.md](reference.md)
- Interactive preview: open `design_system/Ayron/ui_kits/ayron-app/index.html`
