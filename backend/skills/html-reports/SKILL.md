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

## Workspace

Los reportes HTML se editan en el **filesystem del agente** bajo `/workspace/artifacts/`:

| Path | Uso |
|------|-----|
| `/workspace/artifacts/_draft.html` | Borrador nuevo antes del primer publish |
| `/workspace/artifacts/{file_id}.html` | Artifact publicado o en edición |

Lee starters y guías desde `/skills/html-reports/` (solo lectura). **No escribas en `/skills/**`** — copia al workspace.

## Tools

| Tool | Uso |
|------|-----|
| `write_file` / `edit_file` / `grep` | Editar HTML en el workspace |
| `hydrate_html_artifact` | Cargar artifact publicado al workspace para editar |
| `validate_html_artifact` | Sanitizar y escribir versión canónica al path |
| `publish_html_artifact` | Publicar path validado al usuario |
| `list_conversation_files` | Listar archivos con `file_id` |

## Flujos

### Crear reporte o dashboard nuevo

0. **Planifica** con `write_todos`. El último paso: **Publicar artifact**.
1. Lee **`/skills/html-reports/GUIDELINES.md`** (y `starter-dashboard.html` si aplica)
2. Escribe HTML en `/workspace/artifacts/_draft.html` con `write_file` o `edit_file`
3. `validate_html_artifact("/workspace/artifacts/_draft.html")`
4. `publish_html_artifact(path, title, subtitle=..., filename=...)`
5. No repitas contenido en el chat

### Editar artifact existente

1. `hydrate_html_artifact(file_id)` → carga en `/workspace/artifacts/{file_id}.html`
2. Edita con `read_file` / `grep` / `edit_file`
3. `validate_html_artifact(path)`
4. `publish_html_artifact(path, title=..., file_id=...)`
5. **No** uses `_draft.html` ni publiques sin `file_id` para el mismo entregable

### Dashboard grande

Escribe el HTML completo en el workspace por secciones con `edit_file`. No hay flujo incremental separado: el borrador vive en el workspace hasta `publish_html_artifact`.

## Dos tipos de entregable

| Tipo | Cuándo | Wrapper raíz | Al hacer click |
|------|--------|--------------|----------------|
| **Reporte** | Explainers, postmortems, briefs | `.ay-report-prose` | Panel lateral, export PDF |
| **Dashboard** | KPIs, tablas, status analítico | `.ay-dash-page` | Vista expandida |

## Interactividad declarativa

**Prefiere dashboards interactivos** cuando haya varias vistas, periodos o escenarios.

**Tabs de página y filtros van arriba del dashboard** — al inicio de `.ay-dash-inner`, antes del grid de contenido (insight, KPIs, tablas). No los insertes en medio del informe.

**No incluyas** eyebrow, `.ay-dash-title`, `.ay-dash-subtitle` ni `.ay-dash-divider` en el HTML por ahora (el título va en metadata de `publish_html_artifact`).

Usa:

- **Tabs de página** — capítulos grandes; arriba en `.ay-dash-inner`
- **Tabs por sección** — `.ay-dash-tabs--section` dentro de una columna del grid
- **Tabs en header** — `.ay-dash-tabs--header` + `data-panels-target` dentro de `.ay-dash-tab-scope`
- **Filtros legacy** — `.ay-dash-filter-bar` arriba + JSON
- **Dashboard analítico** — `.ay-dash-filter-scope` + dataset JSON + slicers (ver GUIDELINES y `starter-analytics-dashboard.html`)
- **Tablas ordenables** — `ay-dash-table--sortable`
- **Calculadoras what-if** — `.ay-dash-calculator`

Ver GUIDELINES para markup exacto. No escribas `<input>`, `<button>` ni handlers en HTML.

## Gráficos en el reporte

Incrusta gráficos Chart.js con bloques `.ay-chart` y JSON en `<script type="application/json">`. No uses `show_chart` aparte si el gráfico va dentro del informe.

## Insight primero

En dashboards, el bloque **insight** va **al inicio del grid** (o del panel de tab activo), antes de KPIs y tablas — **después** de filtros y tabs de página si los hay.

## Ejemplo crear dashboard

```
# 1. write_file("/workspace/artifacts/_draft.html", html_from_guidelines)
# 2. validate_html_artifact("/workspace/artifacts/_draft.html")
# 3. publish_html_artifact(
#      path="/workspace/artifacts/_draft.html",
#      title="Ventas Mayo 2026",
#      subtitle="Chinook · facturación",
#      filename="ventas-mayo-2026.html",
#    )
```

## Anti-patrones

- Publicar sin `validate_html_artifact` antes
- Escribir en `/skills/**` en lugar del workspace
- Crear otro artifact (`_draft` + publish sin `file_id`) cuando el usuario pidió **modificar** uno existente
- Colocar **tabs de página** o **filtros** en medio del grid
- `<script>` o handlers inline (salvo JSON en `type="application/json"`)
- Volcar el informe en markdown en el chat

## Reglas en el chat

- El artifact aparece como tarjeta HTML **solo tras `publish_html_artifact`**
- **Dashboard**: vista expandida al click
- **Reporte**: panel lateral, export PDF
- No repitas el contenido en tu respuesta
