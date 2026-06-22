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

## Interactividad y JavaScript

**Escribe toda la lógica del dashboard en el HTML del workspace** — filtros, tabs, KPIs dinámicos, gráficos, tablas ordenables, calculadoras. El frontend **solo renderiza** el artifact en un iframe sandbox; **no** monta runtime Ayron (`AyronDashboard`, `AyronChart`).

Incluye en tu HTML:

- Markup semántico con clases `ay-dash-*` / `ay-report-prose` (Ayron inyecta fuentes y CSS del design system en preview/export)
- `<script>` inline con la lógica (event listeners, agregaciones, render)
- `<script type="application/json">` para datasets grandes
- `<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js">` si usas Chart.js (único CDN externo permitido)
- `<button>`, `<select>`, `<input>` según necesites — **no** uses handlers inline (`onclick=`); enlaza en JS

Al publicar, `validate_html_artifact` preserva scripts inline y JSON; elimina scripts externos no permitidos.

Ver **`starter-analytics-dashboard.html`** para un dashboard analítico autocontenido con filtros, KPIs, tabla y gráfico.

## Gráficos en el reporte

Incrusta Chart.js con `<script src="…chart.js…">` y tu propio script de inicialización sobre `<canvas>`. No dependas de bloques `.ay-chart` montados por el chat — declara el canvas y construye el chart en JS.

## Anti-patrones

- Publicar sin `validate_html_artifact` antes
- Escribir en `/skills/**` en lugar del workspace
- Crear otro artifact (`_draft` + publish sin `file_id`) cuando el usuario pidió **modificar** uno existente
- Depender de `AyronDashboard.mountAll` / `AyronChart.mountAll` en el chat
- `<script src>` a dominios distintos de Chart.js en jsdelivr
- Volcar el informe en markdown en el chat

## Reglas en el chat

- El artifact aparece como tarjeta HTML **solo tras `publish_html_artifact`**
- **Dashboard**: vista expandida al click
- **Reporte**: panel lateral, export PDF
- No repitas el contenido en tu respuesta
