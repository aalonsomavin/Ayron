Inline data table for agent chat answers. Wrap in a Card with border only — no shadow in chat.

```html
<div class="ay-data-table">
  <div class="ay-card ay-data-table__card">
    <div class="ay-data-table__grid">
      <div class="ay-data-table__head">…</div>
      <div class="ay-data-table__row">…</div>
    </div>
    <div class="ay-data-table__caption">Top 5 of 120 artists</div>
  </div>
</div>
```

When to use:
- Agent presents tabular query results with ≤25 rows and ≤12 columns.
- Prefer after fetching data — not for schema introspection or long raw dumps.
- No table title — context lives in the agent's text message above the table.
- Do not duplicate table data in prose after calling `show_data_table`.

Column widths (inferred by default; optional override via `column_widths`):
- `narrow` — IDs, short numeric codes.
- `auto` — fit cell content up to a max width.
- `fill` — main text column; expands and wraps.
- Example override: `["narrow", "fill", "narrow"]` for album id, name, artist id.

Anatomy:
- Header row: `--ay-bg-subtle`, uppercase 11.5px, `--ay-text-subtle`.
- Data rows: hairline `--ay-border-subtle`, 14px body, 11px vertical padding.
- Numeric/metric cells: `--ay-font-mono`, 13px, left-aligned (`.ay-data-table__cell--mono`).
- Optional caption: 12px, `--ay-text-muted` — use for truncation context.

Rules:
- Light mode only. No emoji. Sentence case in headers.
- Borders carry separation; no gradients or large color fills.
- More than 25 rows → aggregate in SQL or show top-N plus caption.
- Column headers in plain language (Spanish in product), not raw SQL names.
