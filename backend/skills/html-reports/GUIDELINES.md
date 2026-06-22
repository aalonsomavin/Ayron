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

**Gráfico de torta (pie)** — una sola serie; usa `color_indices` (uno por segmento), no `color_index`:

```html
<div class="ay-dash-col ay-dash-col--6">
  <div class="ay-chart" data-chart-id="chart-categorias">
    <script id="chart-categorias" type="application/json">
    {"chart_type":"pie","title":"Ventas por categoría","caption":"Mayo 2026","labels":["Rock","Jazz","Clásica"],"datasets":[{"label":"Ventas","data":[42,28,18],"color_indices":[0,1,2]}],"value_format":"percent"}
    </script>
    <div class="ay-chart__card">
      <div class="ay-chart__title">Ventas por categoría</div>
      <div class="ay-chart__plot"><canvas class="ay-chart__canvas"></canvas></div>
      <div class="ay-chart__caption">Mayo 2026</div>
    </div>
  </div>
</div>
```

Reglas del gráfico:
- `chart_type`: `bar`, `line` o `pie`
- `labels`: máx. 25; `datasets`: máx. 8 series (pie: una sola)
- `bar` / `line`: `color_index` por serie (0–7)
- `pie`: `color_indices` con un índice por segmento (`[0,1,2,…]`); si omites `color_indices`, Ayron asigna colores automáticamente
- Valores numéricos en `data`, no strings formateados
- `value_format`: `number`, `currency` o `percent`
- El `id` del `<script>` debe coincidir con `data-chart-id` del wrapper
- Ayron inyecta Chart.js y monta el canvas — no añadas `<script src>` ni JS
- En PDF el gráfico puede no renderizar (WeasyPrint); el HTML descargable sí

## Interactividad (dashboards)

**Usa interactividad cuando el informe lo mejore** — no dejes dashboards estáticos si hay varias dimensiones (periodo, región, escenario, producto) o datos que el usuario querrá explorar. Ayron monta tabs, filtros, tablas ordenables y calculadoras; declara markup + JSON, sin JS propio.

| Patrón | Cuándo |
|--------|--------|
| **Tabs por sección** | 2–5 vistas del mismo bloque (trimestres, regiones, escenarios) |
| **Tabs de página** | Capítulos grandes del informe (Resumen / Detalle / Anexos) |
| **Filtros** | Una tabla o bloque que filtra por dimensión |
| **Tabla ordenable** | Rankings, listas largas |
| **Calculadora** | What-if, proyecciones, sensibilidad |

### Tabs — tres niveles

**Tabs de página van arriba** — en el shell, al inicio de `.ay-dash-inner` (después de filtros globales si los hay). Cada panel lleva su propio grid con insight → KPIs → detalle.

**1. Página completa** — shell en create, cada capítulo con append `target="tabs"`. **Solo** paneles de capítulo aquí (Resumen, Detalle…). Los años, regiones u otras sub-vistas van en tabs de sección (`--section`) dentro del contenido del panel, **nunca** con `target="tabs"`.

```html
<div class="ay-dash-tabs">
  <div class="ay-dash-tab-panels">
    <div class="ay-dash-tab-panel" data-page="ventas" data-label="Ventas">
      <div class="ay-dash-grid">…</div>
    </div>
    <div class="ay-dash-tab-panel" data-page="clientes" data-label="Clientes">
      <div class="ay-dash-grid">…</div>
    </div>
  </div>
</div>
```

**2. Sección dentro del grid** — tabs que cambian solo ese bloque (`.ay-dash-tabs--section`). Si van dentro de un panel de página, inclúyelos en el HTML del panel con `target="grid"`, no con `target="tabs"`:

```html
<div class="ay-dash-col ay-dash-col--12">
  <div class="ay-dash-tabs ay-dash-tabs--section">
    <div class="ay-dash-tab-panels">
      <div class="ay-dash-tab-panel" data-page="q1" data-label="Q1">
        <div class="ay-dash-grid">
          <div class="ay-dash-col ay-dash-col--3">
            <div class="ay-dash-card">
              <div class="ay-dash-kpi-label">Ingresos</div>
              <div class="ay-dash-kpi-value">€420K</div>
            </div>
          </div>
        </div>
      </div>
      <div class="ay-dash-tab-panel" data-page="q2" data-label="Q2">
        <div class="ay-dash-grid">…</div>
      </div>
    </div>
  </div>
</div>
```

**3. Tabs en header de card** — selector arriba, contenido debajo (`data-panels-target`):

```html
<div class="ay-dash-col ay-dash-col--12">
  <div class="ay-dash-tab-scope">
    <div class="ay-dash-card ay-dash-card--flush">
      <div class="ay-dash-card-header ay-dash-card-header--with-tabs">
        <span class="ay-dash-card-header__title">Ventas por región</span>
        <div class="ay-dash-tabs ay-dash-tabs--header" data-panels-target="#ventas-region"></div>
      </div>
    </div>
    <div id="ventas-region" class="ay-dash-tab-panels">
      <div class="ay-dash-tab-panel" data-page="norte" data-label="Norte">
        <div class="ay-dash-card ay-dash-card--flush">
          <table class="ay-dash-table ay-dash-table--sortable">…</table>
        </div>
      </div>
      <div class="ay-dash-tab-panel" data-page="sur" data-label="Sur">
        <div class="ay-dash-card ay-dash-card--flush">
          <table class="ay-dash-table">…</table>
        </div>
      </div>
    </div>
  </div>
</div>
```

Puedes anidar varios `.ay-dash-tab-scope` en el mismo dashboard. Combina tabs de sección con filtros o calculadoras en otras columnas.

**Filtros van arriba** — `.ay-dash-filter-bar` o `.ay-dash-filter-scope` al inicio de `.ay-dash-inner`, antes del grid. No los coloques debajo de KPIs ni al final del informe.

**Filtros legacy** — barra con JSON; filas con atributo `data-region` (o el que definas):

```html
<div class="ay-dash-filter-bar">
  <script type="application/json">
  {"filters":[{"id":"region","label":"Región","options":["Todas","Norte","Sur"],"target":"#tabla-ventas","attr":"data-region"}]}
  </script>
</div>
<table id="tabla-ventas" class="ay-dash-table">…<tr data-region="Norte">…</tr>…</table>
```

**Dashboard analítico coordinado** — usa `.ay-dash-filter-scope` cuando necesites filtros multi-select, KPIs reactivos, gráficos que se actualizan y cross-filter (clic en barra). **Colócalo arriba** (inicio de `.ay-dash-inner`). Copia la estructura de `starter-analytics-dashboard.html`.

```html
<div class="ay-dash-filter-scope">
  <script type="application/json" id="analytics-data">{"rows":[…]}</script>
  <script type="application/json">{"slicers":[{"id":"year","field":"year","label":"Año","control":"pills"},{"id":"country","field":"country","label":"País","control":"dropdown"},…]}</script>
  <div class="ay-dash-slicer-bar"></div>
  <div class="ay-dash-filter-chips"></div>
  <div class="ay-dash-grid">…tiles…</div>
</div>
```

Reglas del scope coordinado:
- **Dataset obligatorio** — primer script JSON con `"rows": […]` (resultado SQL del agente)
- **Config slicers** — segundo script con `"slicers": [{"id","field","label","control"}, …]`
- **Control del slicer** — `"control": "pills"` para pocas opciones visibles (p. ej. años); `"control": "dropdown"` para listas largas (país, género) con checkboxes multi-select. Si omites `control`, Ayron usa pills en valores numéricos (años) y dropdown en texto
- **KPIs live** — `.ay-dash-kpi-live` + `data-agg="sum:amount"` (o `count`, `count_distinct:field`) + `data-format="currency|number|percent"`
- **Gráficos live** — `.ay-chart.ay-chart--live` + `data-dimension` + `data-measure`; JSON solo metadata (`title`, `caption`, `chart_type`, `value_format`) — **no** pongas `labels` ni `data` en charts live
- **Cross-filter** — en barras categóricas añade `data-cross-filter` con el id del slicer (p. ej. `country`)
- **Tablas** — filas con `data-{field}` por cada dimensión filtrable (`data-year`, `data-country`, …)
- **Grid de charts** — `.ay-dash-grid.ay-dash-grid--charts` para layout asimétrico (line arriba, bars abajo)

Cuándo usar scope vs filtros legacy: scope para análisis exploratorio con varias dimensiones coordinadas; `.ay-dash-filter-bar` para filtrar una sola tabla con un `<select>`.

**Tabla ordenable** — añade `ay-dash-table--sortable`; columnas numéricas con `ay-dash-th-numeric` en `<th>`.

**Calculadora / what-if** — bloque `.ay-dash-calculator` con inputs + fórmulas → KPIs en vivo. Ayron genera los inputs; no escribas `<input>` en HTML.

Cuándo usarlo: proyecciones, ROI, sensibilidad, simuladores simples.

```html
<div class="ay-dash-calculator">
  <script type="application/json">
  {
    "inputs": [
      {"id": "units", "label": "Unidades", "type": "number", "default": 1000, "min": 0},
      {"id": "price", "label": "Precio unitario", "type": "number", "default": 42.5, "min": 0, "step": 0.01}
    ],
    "constants": {"fixed_cost": 30000},
    "outputs": [
      {"id": "revenue", "label": "Ingresos", "expr": "units * price", "format": "currency"},
      {"id": "margin", "label": "Margen", "expr": "(revenue - fixed_cost) / revenue", "format": "percent"}
    ]
  }
  </script>
  <div class="ay-dash-grid">
    <div class="ay-dash-col ay-dash-col--3" data-calc-input="units">
      <div class="ay-dash-card ay-dash-card--calc-input"></div>
    </div>
    <div class="ay-dash-col ay-dash-col--3" data-calc-input="price">
      <div class="ay-dash-card ay-dash-card--calc-input"></div>
    </div>
    <div class="ay-dash-col ay-dash-col--3" data-calc-output="revenue">
      <div class="ay-dash-card ay-dash-card--calc-output">
        <div class="ay-dash-kpi-label">Ingresos</div>
        <div class="ay-dash-kpi-value ay-dash-kpi-value--calc">—</div>
      </div>
    </div>
    <div class="ay-dash-col ay-dash-col--3" data-calc-output="margin">
      <div class="ay-dash-card ay-dash-card--calc-output">
        <div class="ay-dash-kpi-label">Margen</div>
        <div class="ay-dash-kpi-value ay-dash-kpi-value--calc">—</div>
      </div>
    </div>
  </div>
</div>
```

**Calc cards — layout y CSS (importante)**

Usa **solo clases del design system**. No CSS inline ni estilos custom.

| Tipo | Markup del agente | Label |
|------|-------------------|-------|
| **Input** | `<div class="ay-dash-col ay-dash-col--N" data-calc-input="{id}"><div class="ay-dash-card ay-dash-card--calc-input"></div></div>` | Solo en JSON `inputs[].label` — **no** pongas `ay-dash-kpi-label` en input slots |
| **Output** | `<div class="ay-dash-col ay-dash-col--N" data-calc-output="{id}"><div class="ay-dash-card ay-dash-card--calc-output"><div class="ay-dash-kpi-label">…</div><div class="ay-dash-kpi-value ay-dash-kpi-value--calc">—</div></div></div>` | En HTML (sentence case) — debe coincidir con `outputs[].label` |

**Anchos de columna:** `ay-dash-col--2` parámetros compactos · `--3` default · `--4` inputs largos · `--6` resultados destacados.

**Evita:** labels duplicados en input cards, ALL CAPS en labels (usa sentence case), `<input>` manual, cards sin `ay-dash-card--calc-input` / `--calc-output`.

Reglas calculadora v1:
- `inputs[].type`: `number`, `range`, `select` (escenarios con `options[].values` inyectan variables al scope)
- **Slots de input:** `[data-calc-input="{id}"]` + card vacía `ay-dash-card ay-dash-card--calc-input`. Label solo en JSON.
- **Sin slot:** el input cae en `.ay-dash-calculator__controls` (barra agrupada).
- **Slots output:** `[data-calc-output="{id}"]` + `ay-dash-card--calc-output` + kpi-label + kpi-value--calc.
- `outputs[].expr`: aritmética `+ - * / ( )`, identificadores de inputs/constants/outputs previos, funciones `min`, `max`, `round`, `abs`
- `outputs[].format`: `number`, `currency`, `percent` (percent espera ratio 0–1, p. ej. `0.15` → `15.0%`)
- En PDF/export: KPIs con valores default

En PDF/export descargable los filtros, tabs y calculadoras quedan en estado por defecto (primera tab, sin filtro, inputs default).

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
- Usar filtros, tablas ordenables y calculadoras cuando haya datos comparables
- Usar tablas HTML semánticas con clases dashboard
- Añadir diagramas SVG en reportes prosa
- Incrustar gráficos `.ay-chart` con Chart.js en dashboards o prosa
- Repetir patrones del starter adaptando datos

Evita:
- Publicar sin `validate_html_artifact` antes de `publish_html_artifact`
- Bloques JSON o tools distintas de las de html-reports para armar el informe
- Colocar **tabs de página** o **filtros** en medio del grid o al final del dashboard
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
