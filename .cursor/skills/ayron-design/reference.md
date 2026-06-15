# Ayron Design System — Quick Reference

Source of truth: `design_system/Ayron/`. Read token files for the full scale.

## Semantic tokens (use these in product code)

### Surfaces & text
- `--ay-bg`, `--ay-bg-subtle`, `--ay-bg-muted`
- `--ay-surface`, `--ay-surface-hover`, `--ay-surface-sunken`
- `--ay-text`, `--ay-text-muted`, `--ay-text-subtle`, `--ay-text-disabled`, `--ay-text-inverse`, `--ay-text-link`

### Actions & accents
- `--ay-primary`, `--ay-primary-hover`, `--ay-primary-text` — ink buttons
- `--ay-accent` — focus/selection/links (not large fills)
- `--ay-selection-bg` — selected row/item tint

### Borders & shadows
- `--ay-border`, `--ay-border-strong`
- `--ay-shadow-xs` … `--ay-shadow-lg`, `--ay-shadow-focus`

### Charts
- `--ay-chart-1` … `--ay-chart-8` — categorical palette

### Typography
- `--ay-font-sans`, `--ay-font-mono`
- Scale: `--ay-text-display`, `--ay-text-h1` … `--ay-text-xs`, `--ay-text-body` (15px)
- Weights: `--ay-weight-regular` (400) through `--ay-weight-bold` (700)
- Tracking: `--ay-tracking-tight` (-0.02em) for headings

### Spacing & layout
- `--ay-space-*` — 4px base grid
- App chrome: 256px sidebar, 1200px content container

### Effects
- Radii: `--ay-radius-sm` (6px), `--ay-radius-md` (8px), `--ay-radius-lg` (12px), `--ay-radius-full`
- Motion: `--ay-ease`, `--ay-dur-fast` (120ms), `--ay-dur-normal` (180ms)

## Core components

Each lives in `design_system/Ayron/components/core/` with `.jsx`, `.d.ts`, `.prompt.md`.

| Component | Key API |
|-----------|---------|
| **Button** | `variant`: primary \| secondary \| ghost \| danger \| link. `size`: sm \| md \| lg. One primary per view. |
| **Input** | Bordered field with focus ring. See `.prompt.md`. |
| **Badge** | Status/count chips. Semantic colors only in status contexts. |
| **Card** | White, `--ay-radius-lg`, 1px border, optional `--ay-shadow-sm`. |
| **Tabs** | Underline or contained. See `.prompt.md`. |
| **Switch** | On/off for automations and settings. |
| **Avatar** | User/entity initials or image. `--ay-radius-full`. |
| **Icon** | Lucide-based inline SVG set in `components/icons/`. |

## Interactive states

- **Hover:** surfaces → `--ay-surface-hover`; primary buttons → `--ay-primary-hover`
- **Focus:** `--ay-shadow-focus` (3px blue ring) — always visible
- **Selected:** `--ay-selection-bg` + blue marker/border
- **Disabled:** `--ay-text-disabled`, no shadow

## Copy patterns

- Buttons: "Connect a source", "Ask Ayron", "New automation"
- Errors: state what happened + next step ("Couldn't reach the warehouse. Check credentials and retry.")
- Empty states: invite first action ("No sources yet. Connect one to start asking questions.")

## Product UI kit screens

`design_system/Ayron/ui_kits/ayron-app/`:

- `AppShell.jsx` — sidebar + top bar + router
- `ChatScreen.jsx` — agent chat, artifacts, composer
- `ArtifactPanel.jsx` — document/spreadsheet viewer
- `DashboardScreen.jsx` — KPIs, charts, tables
- `SourcesScreen.jsx` — connected sources + catalog
- `AutomationsScreen.jsx` — workflow cards with switches
