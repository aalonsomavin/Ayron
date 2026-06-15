---
name: ayron-design
description: Use this skill to generate well-branded interfaces and assets for Ayron (an AI agent for data analytics), either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the `readme.md` file within this skill, and explore the other available files.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

## Quick map
- `styles.css` — link this one file to get all tokens + fonts.
- `tokens/` — colors, typography, spacing, effects (CSS custom properties, `--ay-*`).
- `components/core/` — Button, Input, Badge, Card, Tabs, Switch, Avatar (React, `.jsx` + `.d.ts` + `.prompt.md`).
- `components/icons/` — `Icon` component (Lucide-based inline SVG set).
- `ui_kits/ayron-app/` — interactive product kit (chat, dashboard, sources, automations).
- `guidelines/` — foundation specimen cards.
- `assets/logo/` — placeholder brand marks.

## Non-negotiables
- Light mode only. Near-monochrome: ink (`--ay-primary`) for primary actions, white/faint-gray surfaces, hairline borders.
- One restrained blue (`--ay-accent`) for focus / selection / links / primary chart series — never large fills.
- Geist for UI, Geist Mono for data/metrics/code. Sentence case everywhere. No emoji in product UI.
- Soft shadows; borders do most separation. ~8px radii. Quick, restrained motion (120–180ms).
