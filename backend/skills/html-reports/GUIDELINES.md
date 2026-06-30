# Guidelines — reportes HTML Ayron

Lee este archivo antes de escribir HTML para el workspace (`/workspace/artifacts/`). Ayron inyecta automáticamente las fuentes Geist y el CSS del design system — **no repitas `<link>` ni `<style>` del sistema** en tu fragmento.

## Fundamentos visuales

- Light mode, estética dev-tool: limpia, técnica, near-monochrome
- **Geist** para UI; **Geist Mono** para métricas, cifras en tablas y deltas
- Sentence case en títulos y labels; sin emoji
- Superficies: blanco `#ffffff`, fondo dashboard `#f4f4f5`, bordes `#e6e6e8`
- Texto: ink `#18181b`, muted `#62626b`, subtle `#8a8a92`
- Accent `#3b6ef6` solo en puntos pequeños (dot del eyebrow, tags, callout border)
- Delta positivo `#15803d`; negativo `#b91c1c`
- Cards: borde hairline + sombra suave; radius ~12px
- Profundidad con bordes y sombras, no gradientes en superficies

## Dos tipos de entregable

| Tipo | Cuándo | Wrapper raíz | UX en el chat |
|------|--------|--------------|---------------|
| **Dashboard** | KPIs, tablas, status con cifras, informes analíticos | `.ay-dash-page` | Click → vista expandida a pantalla completa |
| **Reporte (prosa)** | Explainers, postmortems, briefs técnicos, aprendizaje | `.ay-report-prose` | Click → panel lateral, tamaño documento, export PDF |

El tipo se infiere del wrapper raíz. El HTML que ya generas con `.ay-dash-page` es el formato correcto para dashboards.

## Dos modos de reporte

| Modo | Cuándo | Wrapper raíz | UX |
|------|--------|--------------|-----|
| **Dashboard** | KPIs, tablas, status con cifras, informes analíticos | `.ay-dash-page` | Expandido al click |
| **Prosa** | Explainers, postmortems, briefs técnicos, aprendizaje | `.ay-report-prose` | Panel lateral, PDF |

Usa **solo clases `ay-dash-*` / `ay-report-prose`** — evita CSS inline duplicado. Inline permitido solo para valores dinámicos (p. ej. `width:62%` en barras de progreso).

## Dashboard — layout

Shell mínimo:

```html
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <div class="ay-dash-filter-scope">…</div>
    <div class="ay-dash-tabs">
      <div class="ay-dash-tab-panels">…</div>
    </div>
    <div class="ay-dash-grid">
      …
    </div>
  </div>
</div>
```

**Header de página (eyebrow, título, subtítulo, divider)** — omitir por ahora. El título del informe va en metadata de `publish_html_artifact`, no en el HTML del dashboard.

Plantilla completa con ejemplos: lee `/skills/html-reports/starter-dashboard.html`.

### Orden del contenido

**Tabs de página y filtros van arriba** — al inicio de `.ay-dash-inner`, **antes** del grid de contenido. No los entierres entre KPIs, tablas o gráficos.

Orden vertical recomendado:

1. **Filtros** (si aplica) — `.ay-dash-filter-bar` o `.ay-dash-filter-scope`
2. **Tabs de página** (si aplica) — `.ay-dash-tabs` de capítulo completo; si hay filtros globales y tabs, **filtros primero**, luego tabs
3. Contenido — insight, KPIs, gráficos, tablas (ver abajo)

Dentro del contenido, **el insight va primero** — como primer bloque del grid (o del panel de tab activo). Resume el hallazgo principal antes de KPIs, tablas o detalle. Si hay varios insights, el más importante primero; el resto puede ir después de los KPIs.

Orden recomendado **dentro del grid** (o dentro de cada panel de tab):

1. Insight (`.ay-dash-card--insight`) — ancho completo (`ay-dash-col--12`) o 7–12 cols
2. KPIs / metric strip
3. Tablas, rankings, barras, gráficos
4. Callouts o insights secundarios

**Tabs por sección** (`--section`) y **tabs en header** (`--header`) no van a nivel de página: van **arriba de su bloque** (columna o card), no sustituyen la regla de tabs/filtros globales.

En prosa, el equivalente es el **TL;DR** al inicio (ya va antes del cuerpo).

### Grid

- `.ay-dash-grid` — 12 columnas, gap 20px
- Columnas: `.ay-dash-col ay-dash-col--3|5|6|7|12`

### Patrones (combínalos libremente)

**KPI card**
```html
<div class="ay-dash-col ay-dash-col--3">
  <div class="ay-dash-card">
    <div class="ay-dash-kpi-label">Ingresos</div>
    <div class="ay-dash-kpi-value" data-ay-claim="kpi-revenue">$1.28M</div>
    <div class="ay-dash-delta ay-dash-delta--up">…12.4%…<span class="ay-dash-delta__muted">vs mes anterior</span></div>
  </div>
</div>
```
Variantes: `.ay-dash-kpi-value--sm`, `.ay-dash-kpi-value--hero`, `.ay-dash-kpi-row` + `.ay-dash-kpi-icon`, `.ay-dash-delta--down`

**Trazabilidad (claims)** — en KPIs alimentados por SQL, añade `data-ay-claim="{claim_key}"` en `.ay-dash-kpi-value` (o en el contenedor del gráfico). Usa claves estables en kebab-case (`kpi-total-revenue`, `chart-by-region`). Cada `run_sql_query` exitoso devuelve un `source_ref` corto (`sql_1`, `sql_2`, …). Copia esos refs al publicar con `provenance[]` en `publish_html_artifact`:

```json
{
  "provenance": [
    {
      "claim_key": "kpi-total-revenue",
      "label": "Ingresos totales",
      "source_refs": ["sql_1"],
      "definition": {
        "metric": "SUM(total)",
        "dataset_ref": "embedded:analytics-data",
        "base_filters": "sin filtros de fecha"
      },
      "transformation": "SUM(total) · redondeo 2 dec"
    }
  ]
}
```

Un KPI puede referenciar varios `source_refs` si combina datos de varias consultas. No uses IDs de otras tools (p. ej. el `tool_call_id` de `publish_html_artifact`).

Cada `claim_key` del array debe existir en el HTML como `data-ay-claim`. El manifiesto se guarda solo en `File.content_json.provenance` — no incluyas `#ay-provenance-manifest` ni JSON de linaje en el DOM.

En Analíticas, el usuario puede hacer clic en un KPI con `data-ay-claim` para abrir el panel de procedencia. Ayron inyecta el bridge automáticamente al publicar dashboards.

**Metric strip** — `.ay-dash-card.ay-dash-strip` con `.ay-dash-strip__item` / `__divider`

**Tabla con header** — `.ay-dash-card.ay-dash-card--flush` + `.ay-dash-card-header` + `table.ay-dash-table`
Celdas: `.ay-dash-td-strong`, `.ay-dash-td-muted`, `.ay-dash-td-mono`, `.ay-dash-td-right`, `.ay-dash-td-rank`

**Barras inline** — `.ay-dash-bar-row` con `.ay-dash-bar-track` > `.ay-dash-bar-fill` (width inline). Colores: `.ay-dash-bar-fill--green|orange|purple`

**Insight** — `.ay-dash-card.ay-dash-card--insight` + `.ay-dash-insight-head` con `.ay-dash-insight-logo` vacío (Ayron inyecta el mark automáticamente; no pongas SVG, emoji ni símbolos propios) + `.ay-dash-insight-brand` «Ayron» + `.ay-dash-insight-kind` «insight» + `.ay-dash-insight-text` + `.ay-dash-tags` / `.ay-dash-tag--accent|neutral`. Copia la estructura de `starter-dashboard.html` tal cual.

**Callout** — `.ay-dash-callout` + `.ay-dash-callout-stats` / `.ay-dash-callout-stat`

**Gráfico Chart.js** — incluye Chart.js y tu script de init. Ayron **no** monta gráficos en el chat; el artifact debe ser autocontenido.

```html
<div class="ay-dash-col ay-dash-col--12">
  <div class="ay-dash-card ay-dash-card--flush">
    <div class="ay-dash-card-header">
      <span class="ay-dash-card-header__title">Ingresos por región</span>
    </div>
    <div class="ay-chart__plot" style="padding:16px 20px 20px;height:280px;">
      <canvas id="chart-ventas"></canvas>
    </div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function () {
  new Chart(document.getElementById("chart-ventas"), {
    type: "bar",
    data: {
      labels: ["EMEA", "APAC"],
      datasets: [{ label: "Ingresos", data: [486200, 248910], backgroundColor: "#3b6ef6" }]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });
});
</script>
```

Reglas:
- Único CDN externo permitido: Chart.js en jsdelivr
- Valores numéricos en `data`, no strings formateados
- Moneda: prefijo `$` + `toLocaleString("es-MX")`; indica la moneda en labels/caption \
  (ej. «pesos mexicanos»), no en el símbolo del valor
- En PDF el gráfico puede no renderizar (WeasyPrint); el HTML descargable sí

## Interactividad (dashboards)

**Implementa toda la interactividad en JavaScript** dentro del HTML del workspace. El chat renderiza el artifact en un iframe sandbox — no hay runtime `AyronDashboard` / `AyronChart`.

| Patrón | Cómo implementarlo |
|--------|-------------------|
| **Tabs** | Markup con paneles + `<button>` + JS que alterna clases `hidden` / `aria-selected` |
| **Filtros / slicers** | `<button>` o `<select>` + JS que filtra filas y recalcula KPIs |
| **Tabla ordenable** | Clic en `<th>` + JS que reordena `<tbody>` |
| **Calculadora what-if** | `<input type="number">` + JS con fórmulas |
| **Gráficos reactivos** | Actualiza instancias Chart.js en tu función `render()` |

**Filtros van arriba** — al inicio de `.ay-dash-inner`, antes del grid.

**Dashboard analítico** — copia `starter-analytics-dashboard.html`: dataset en `<script type="application/json">`, slicers como botones, KPIs con ids, tabla y chart actualizados en JS.

Puedes usar clases `ay-dash-*` para estilo (slicers, chips, KPI cards) aunque la lógica sea tuya. Datos grandes en JSON; lógica en `<script>` inline al final del fragmento.

**No uses** handlers inline (`onclick=`, `onchange=`). Enlaza eventos en JS.

**Elementos permitidos:** `button`, `input`, `select`, `option`, `textarea`, `label`, `form`.

En PDF/export descargable, el HTML incluye tu JS; WeasyPrint no ejecuta scripts (KPIs estáticos o valores default).

## Prosa — layout

```html
<div class="ay-report-prose">
  <header>
    <h1>Título</h1>
    <p class="ay-report-prose__lead">Una línea de contexto.</p>
  </header>
  <section class="ay-report-prose__tldr"><strong>TL;DR</strong> — …</section>
  <section>
    <h2>Sección</h2>
    <p>…</p>
  </section>
  <footer class="ay-report-prose__sources">
    <h2>Fuentes</h2>
    <ul><li>…</li></ul>
  </footer>
</div>
```

Prosa usa Geist (misma fuente UI del design system). SVG de flujo y `<pre><code>` permitidos. Tablas simples con bordes incluidos en `.ay-report-prose`.

## Libertad del agente

Puedes:
- Inventar layouts dentro del grid (mezclar columnas, añadir secciones)
- Combinar KPI + tablas + insight + callout — **siempre con el insight principal al inicio**
- Usar **tabs por sección** (`ay-dash-tabs--section`) además de tabs de página
- Usar filtros, tablas ordenables y calculadoras con JS propio cuando haya datos comparables
- Usar tablas HTML semánticas con clases dashboard
- Añadir diagramas SVG en reportes prosa
- Incrustar gráficos Chart.js con `<canvas>` + script de init
- Repetir patrones del starter adaptando datos

Evita:
- Publicar sin `validate_html_artifact` antes de `publish_html_artifact`
- Depender de `AyronDashboard` / `AyronChart` en el chat (el artifact debe ser autocontenido)
- Colocar **tabs de página** o **filtros** en medio del grid o al final del dashboard
- Handlers inline (`onclick=`, `onchange=`) — enlaza eventos en `<script>`
- `<script src>` fuera de Chart.js en jsdelivr
- Fuentes genéricas (Inter, system-ui solo como fallback ya incluido)
- Gradientes purple/AI-slop, emoji, exclamaciones
- Volcar el informe en el chat

## Voz (contenido)

- Español, directo, con cifras concretas y ventana temporal
- Métricas con delta cuando aplique
- Insight: 2–4 frases, tags con datos clave
- Fuentes al final en prosa; en dashboard opcional como callout

## Catálogo completo de clases

Todas viven en el CSS inyectado por Ayron (`ay-dash-*`, `ay-report-prose*`). Si dudas de una clase, revisa `starter-dashboard.html` o compón variantes reutilizando las mismas clases base.
