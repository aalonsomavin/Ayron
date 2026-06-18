# Guidelines — reportes HTML Ayron

Lee este archivo antes de escribir HTML para `create_html_report`. Ayron inyecta automáticamente las fuentes Geist y el CSS del design system — **no repitas `<link>` ni `<style>` del sistema** en tu fragmento.

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
    <div class="ay-dash-eyebrow"><span class="ay-dash-eyebrow__dot"></span>Ayron · informe</div>
    <h1 class="ay-dash-title">Título</h1>
    <p class="ay-dash-subtitle">Contexto de una línea.</p>
    <hr class="ay-dash-divider">
    <div class="ay-dash-grid">
      <!-- bloques aquí -->
    </div>
  </div>
</div>
```

Plantilla completa con ejemplos: lee `/skills/html-reports/starter-dashboard.html`.

### Orden del contenido

**El insight va primero** — justo después del header (título, subtítulo, divider), como primer bloque del grid. Resume el hallazgo principal antes de KPIs, tablas o detalle. Si hay varios insights, el más importante primero; el resto puede ir después de los KPIs.

Orden recomendado en dashboard:

1. Insight (`.ay-dash-card--insight`) — ancho completo (`ay-dash-col--12`) o 7–12 cols
2. KPIs / metric strip
3. Tablas, rankings, barras
4. Callouts o insights secundarios

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
    <div class="ay-dash-kpi-value">$1.28M</div>
    <div class="ay-dash-delta ay-dash-delta--up">…12.4%…<span class="ay-dash-delta__muted">vs mes anterior</span></div>
  </div>
</div>
```
Variantes: `.ay-dash-kpi-value--sm`, `.ay-dash-kpi-value--hero`, `.ay-dash-kpi-row` + `.ay-dash-kpi-icon`, `.ay-dash-delta--down`

**Metric strip** — `.ay-dash-card.ay-dash-strip` con `.ay-dash-strip__item` / `__divider`

**Tabla con header** — `.ay-dash-card.ay-dash-card--flush` + `.ay-dash-card-header` + `table.ay-dash-table`
Celdas: `.ay-dash-td-strong`, `.ay-dash-td-muted`, `.ay-dash-td-mono`, `.ay-dash-td-right`, `.ay-dash-td-rank`

**Barras inline** — `.ay-dash-bar-row` con `.ay-dash-bar-track` > `.ay-dash-bar-fill` (width inline). Colores: `.ay-dash-bar-fill--green|orange|purple`

**Insight** — `.ay-dash-card.ay-dash-card--insight` + `.ay-dash-insight-head` con `.ay-dash-insight-logo` vacío (Ayron inyecta el mark automáticamente; no pongas SVG, emoji ni símbolos propios) + `.ay-dash-insight-brand` «Ayron» + `.ay-dash-insight-kind` «insight» + `.ay-dash-insight-text` + `.ay-dash-tags` / `.ay-dash-tag--accent|neutral`. Copia la estructura de `starter-dashboard.html` tal cual.

**Callout** — `.ay-dash-callout` + `.ay-dash-callout-stats` / `.ay-dash-callout-stat`

**Gráfico Chart.js** — `.ay-chart` con payload JSON (mismo formato que el chat). Colócalo en `.ay-dash-col--12` o `--6` dentro del grid, después del insight y antes o junto a tablas según la historia.

```html
<div class="ay-dash-col ay-dash-col--12">
  <div class="ay-chart" data-chart-id="chart-ventas">
    <script id="chart-ventas" type="application/json">
    {"chart_type":"bar","title":"Ingresos por región","caption":"Mayo 2026","labels":["EMEA","APAC"],"datasets":[{"label":"Ingresos","data":[486200,248910],"color_index":0}],"value_format":"currency"}
    </script>
    <div class="ay-chart__card">
      <div class="ay-chart__title">Ingresos por región</div>
      <div class="ay-chart__plot"><canvas class="ay-chart__canvas"></canvas></div>
      <div class="ay-chart__caption">Mayo 2026</div>
    </div>
  </div>
</div>
```

Reglas del gráfico:
- `chart_type`: `bar`, `line` o `pie`
- `labels`: máx. 25; `datasets`: máx. 8 series (pie: una sola)
- Valores numéricos en `data`, no strings formateados
- `value_format`: `number`, `currency` o `percent`
- El `id` del `<script>` debe coincidir con `data-chart-id` del wrapper
- Ayron inyecta Chart.js y monta el canvas — no añadas `<script src>` ni JS
- En PDF el gráfico puede no renderizar (WeasyPrint); el HTML descargable sí

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
- Usar tablas HTML semánticas con clases dashboard
- Añadir diagramas SVG en reportes prosa
- Incrustar gráficos `.ay-chart` con Chart.js en dashboards o prosa
- Repetir patrones del starter adaptando datos

Evita:
- Bloques JSON o tools distintas de `create_html_report`
- CSS inline en cada elemento (copiar estilos del catálogo)
- `<script>` o handlers `onclick`
- Fuentes genéricas (Inter, system-ui solo como fallback ya incluido)
- Gradientes purple/AI-slop, emoji, exclamaciones
- Sparklines o SVG de datos hechos a mano — usa `.ay-chart` con Chart.js
- Volcar el informe en el chat

## Voz (contenido)

- Español, directo, con cifras concretas y ventana temporal
- Métricas con delta cuando aplique
- Insight: 2–4 frases, tags con datos clave
- Fuentes al final en prosa; en dashboard opcional como callout

## Catálogo completo de clases

Todas viven en el CSS inyectado por Ayron (`ay-dash-*`, `ay-report-prose*`). Si dudas de una clase, revisa `starter-dashboard.html` o compón variantes reutilizando las mismas clases base.
