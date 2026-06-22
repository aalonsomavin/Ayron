---
name: html-reports
description: >-
  Create, read, edit, or export HTML reports in the chat. Use for data reports,
  concept explainers, status updates, incident reports, technical briefs, learning
  syntheses, and any deliverable meant for a human to read and share — exportable
  as PDF. The agent writes semantic HTML with Ayron design-system classes. Do NOT
  use for Word (.docx) or chat-only answers. Also use when updating an existing
  HTML report.
---

# Reportes HTML — research, informes y aprendizaje

## Por qué HTML

Los reportes HTML se **leen**; un markdown del mismo tamaño en el chat, no. Usa esta skill
cuando el objetivo es que alguien **absorba información**: explainers, status, postmortems,
briefs técnicos, dashboards, síntesis de código o datos.

## Cuándo usar

- Informe con tablas, KPIs, diagramas o visualizaciones
- Exportación a PDF
- «Resume cómo funciona X» / «Explícame el sistema Y»
- Postmortem, status semanal, brief técnico
- Objetivo de **comprensión o compartir**, no implementación inmediata

No uses para: Word (`.docx`), respuestas solo en chat. Para datos sueltos en el chat sin informe, usa `show_data_table` o `show_chart`.

## Tools

| Tool | Uso |
|------|-----|
| `create_html_report` | Crear reporte o shell de dashboard (`build_mode="complete"` o `"incremental"`) |
| `append_html_report_block` | Añadir bloque a un dashboard en borrador |
| `publish_html_report` | Publicar dashboard borrador (visible al usuario) |
| `update_html_report` | Actualizar reporte publicado por `file_id` |
| `get_html_report` | Leer reporte — devuelve `html` para editar |
| `list_conversation_files` | Listar archivos con `file_id` |

## Flujos

### Reporte pequeño o dashboard simple

0. **Planifica** con `write_todos`. El último paso: **Generar archivo**.
1. Lee **`/skills/html-reports/GUIDELINES.md`**
2. Llama **`create_html_report(title, html, ...)`** con todo el contenido — una tool call
3. No repitas contenido en el chat

### Dashboard grande (incremental)

Usa cuando hay **más de ~4 bloques**, varias páginas/tabs, o muchos datos.

1. `create_html_report(..., build_mode="incremental", html_kind="dashboard")` — shell con header y, arriba, contenedores vacíos para **filtros** y/o **tabs de página** (`ay-dash-tab-panels`) o un `ay-dash-grid` (**no visible aún**)
2. `append_html_report_block(file_id, html, target="grid"|"tabs")` por cada sección
3. **`publish_html_report(file_id)`** — el usuario ve el artifact **solo aquí**
4. Mensaje breve al final

Para editar un archivo ya publicado: `get_html_report` → `update_html_report`

## Dos tipos de entregable

| Tipo | Cuándo | Wrapper raíz | Al hacer click |
|------|--------|--------------|----------------|
| **Reporte** | Explainers, postmortems, briefs | `.ay-report-prose` | Panel lateral, export PDF |
| **Dashboard** | KPIs, tablas, status analítico | `.ay-dash-page` | Vista expandida |

## Interactividad declarativa

**Prefiere dashboards interactivos** cuando haya varias vistas, periodos o escenarios.

**Tabs de página y filtros van arriba del dashboard** — al inicio de `.ay-dash-inner`, antes del grid de contenido (insight, KPIs, tablas). No los insertes en medio del informe.

**No incluyas** eyebrow, `.ay-dash-title`, `.ay-dash-subtitle` ni `.ay-dash-divider` en el HTML por ahora (el título va en metadata de la tool).

Usa:

- **Tabs de página** — capítulos grandes; en el shell, arriba (`append_html_report_block(..., target="tabs")` para cada capítulo)
- **Tabs por sección** — `.ay-dash-tabs--section` dentro de una columna del grid (arriba de ese bloque)
- **Tabs en header** — `.ay-dash-tabs--header` + `data-panels-target` dentro de `.ay-dash-tab-scope`
- **Filtros legacy** — `.ay-dash-filter-bar` arriba + JSON (single-select sobre una tabla)
- **Dashboard analítico** — `.ay-dash-filter-scope` arriba + dataset JSON + slicers (`control: pills|dropdown`) + KPIs/charts live (ver GUIDELINES y `starter-analytics-dashboard.html`)
- **Tablas ordenables** — `ay-dash-table--sortable`
- **Calculadoras what-if** — `.ay-dash-calculator` con slots `[data-calc-input]` / `[data-calc-output]`

Ver GUIDELINES para markup exacto. No escribas `<input>`, `<button>` ni handlers en HTML.

## Gráficos en el reporte

Incrusta gráficos Chart.js con bloques `.ay-chart` y JSON en `<script type="application/json">`. No uses `show_chart` aparte si el gráfico va dentro del informe.

## Insight primero

En dashboards, el bloque **insight** va **al inicio del grid** (o del panel de tab activo), antes de KPIs y tablas — **después** de filtros y tabs de página si los hay.

## Ejemplo dashboard one-shot

```python
create_html_report(
    title="Ventas Mayo 2026",
    subtitle="Chinook · facturación",
    filename="ventas-mayo-2026.html",
    html=\"\"\"
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <div class="ay-dash-grid">
      <div class="ay-dash-col ay-dash-col--12">
        <div class="ay-dash-card ay-dash-card--insight">…</div>
      </div>
    </div>
  </div>
</div>
\"\"\",
)
```

## Ejemplo dashboard incremental

```python
create_html_report(
    title="Ventas Q2",
    build_mode="incremental",
    html_kind="dashboard",
    html=\"\"\"
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <div class="ay-dash-tabs">
      <div class="ay-dash-tab-panels"></div>
    </div>
    <div class="ay-dash-grid"></div>
  </div>
</div>
\"\"\",
)
# file_id del resultado → append_html_report_block(...) × N → publish_html_report(file_id)
```

## Anti-patrones

- Terminar sin `publish_html_report` en flujo incremental
- Mostrar contenido parcial al usuario (append sin publish al final)
- Colocar **tabs de página** o **filtros** en medio del grid o al final del dashboard
- `<script>` o handlers inline
- Volcar el informe en markdown en el chat

## Reglas en el chat

- El artifact aparece como tarjeta HTML **solo al publicar o crear completo**
- **Dashboard**: vista expandida al click
- **Reporte**: panel lateral, export PDF
- No repitas el contenido en tu respuesta
