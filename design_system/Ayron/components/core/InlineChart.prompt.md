Inline chart for agent chat answers. Rendered with Chart.js on a canvas inside a Card (border only — no shadow in chat).

```html
<div class="ay-chart" data-chart-id="chart-123-0">
  <script id="chart-123-0" type="application/json">…</script>
  <div class="ay-card ay-chart__card">
    <div class="ay-chart__title">Ingresos por región</div>
    <div class="ay-chart__plot">
      <canvas class="ay-chart__canvas"></canvas>
    </div>
    <div class="ay-chart__caption">Mayo 2026</div>
  </div>
</div>
```

When to use:
- Agent visualizes aggregated query results with ≤25 labels and ≤8 series.
- `bar`: compare categories (top artists, sales by country).
- `line`: time trends (monthly revenue).
- `pie`: parts of a whole with ≤8 segments; one series only.
- Prefer after fetching data — not for schema introspection.
- Do not duplicate chart data in prose after calling `show_chart`.

Chart types:
- `bar` — vertical grouped bars (Chart.js bar).
- `line` — trend line with point markers (Chart.js line).
- `pie` — proportional slices with legend (Chart.js pie).

Payload (Chart.js-ready):
- `labels`: category or time labels.
- `datasets`: `[{ label, data, color_index }]` (pie uses `color_indices` per slice).
- `value_format`: `number` | `currency` | `percent` for axis ticks and tooltips.

Anatomy:
- Optional title: 13px, weight 600, sentence case, `--ay-text`.
- Plot area: 200px height; Chart.js canvas fills container.
- Series colors: `--ay-chart-1` through `--ay-chart-8`.
- Legend: Chart.js bottom legend when pie or multiple series.
- Optional caption: 12px, `--ay-text-muted`.

Rules:
- Light mode only. No emoji. Sentence case in labels.
- Pass raw numeric values in `series[].values`; formatting is handled client-side.
- More than 25 points → aggregate in SQL or show top-N plus caption.
- Labels in plain language (Spanish in product), not raw SQL names.
- Use Django `json_script` for SSR payload — never raw unescaped JSON in templates.
