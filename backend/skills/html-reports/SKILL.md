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
| `create_html_report` | Crear reporte con HTML (`html=...`) — **una sola llamada** |
| `update_html_report` | Actualizar reporte por `file_id` |
| `get_html_report` | Leer reporte — devuelve `html` para editar |
| `list_conversation_files` | Listar archivos con `file_id` |

## Flujo único

1. Identifica el modo: **dashboard** (KPIs, tablas, cifras) o **prosa** (explainer, postmortem, brief)
2. Lee **`/skills/html-reports/GUIDELINES.md`**
3. Si es dashboard, lee también **`/skills/html-reports/starter-dashboard.html`** como plantilla
4. Escribe HTML con clases del design system y llama **`create_html_report(title, html, ...)`** — todo el informe en **una tool call**
5. No repitas contenido en el chat

Para editar: `get_html_report` → modifica `html` → `update_html_report`

## Dos modos de reporte

| Modo | Cuándo | Wrapper raíz |
|------|--------|--------------|
| **Dashboard** | Ventas, KPIs, status con cifras | `.ay-dash-page` |
| **Prosa** | «Cómo funciona X», postmortem, brief | `.ay-report-prose` |

Ayron inyecta fuentes Geist y CSS (`ay-dash-*`, `ay-report-prose`, `.ay-chart`). **No repitas `<link>` ni `<style>` del sistema** en el fragmento — solo clases documentadas en GUIDELINES.

## Gráficos en el reporte

Incrusta gráficos Chart.js con bloques `.ay-chart` y JSON en `<script type="application/json">` — mismo formato que el chat. Léelo en GUIDELINES. No uses `show_chart` aparte si el gráfico va dentro del informe.

## Insight primero

En dashboards, el bloque **insight** va **al inicio del grid** (después del título), antes de KPIs y tablas. En prosa, el **TL;DR** cumple ese rol al principio.

## Ejemplo dashboard

```python
create_html_report(
    title="Ventas Mayo 2026",
    subtitle="Chinook · facturación",
    filename="ventas-mayo-2026.html",
    html=\"\"\"
<div class="ay-dash-page">
  <div class="ay-dash-inner">
    <h1 class="ay-dash-title">Ventas Mayo 2026</h1>
    <div class="ay-dash-grid">
      <div class="ay-dash-col ay-dash-col--12">
        <div class="ay-dash-card ay-dash-card--insight">…insight al inicio…</div>
      </div>
      <div class="ay-dash-col ay-dash-col--3">
        <div class="ay-dash-card">
          <div class="ay-dash-kpi-label">Ingresos</div>
          <div class="ay-dash-kpi-value">$1.28M</div>
        </div>
      </div>
    </div>
  </div>
</div>
\"\"\",
)
```

## Ejemplo prosa

```python
create_html_report(
    title="Rate limiter — explicación",
    subtitle="Cómo funciona el token bucket en Ayron",
    filename="rate-limiter-explicacion.html",
    html=\"\"\"
<div class="ay-report-prose">
  <header>
    <h1>Rate limiter</h1>
    <p class="ay-report-prose__lead">Token bucket por IP — una lectura.</p>
  </header>
  <section class="ay-report-prose__tldr"><strong>TL;DR</strong> — Cada IP tiene un bucket.</section>
  <section>
    <h2>Flujo</h2>
    <svg viewBox="0 0 400 120" width="100%" height="120" role="img">...</svg>
  </section>
</div>
\"\"\",
)
```

## Patrones

| Patrón | Cuándo | Enfoque |
|--------|--------|---------|
| A Explicador | «Cómo funciona X» | Prosa: TL;DR + SVG + snippets |
| B Status | «Qué entregamos esta semana» | Dashboard: insight + KPIs + tablas |
| C Incidente | Postmortem | Prosa: timeline, secciones |
| D Deep-dive | Aprendizaje | Prosa: secciones + tablas |
| E Decisión | «¿Hacemos X?» | Prosa: recomendación primero |
| F Dashboard | Informe de datos / ventas | Dashboard: insight + KPIs + `.ay-chart` + tablas |

## Anti-patrones

- Volcar el informe en markdown en el chat
- CSS inline duplicado en cada elemento — usa clases de GUIDELINES
- Bloques JSON o múltiples tool calls para armar un informe
- Sparklines o SVG de datos hechos a mano — usa `.ay-chart` dentro del HTML del reporte
- Llamar `show_chart` y además duplicar el gráfico en el reporte
- `<script>` o handlers inline
- Estética genérica (Inter, purple gradients, emoji)

## Reglas en el chat

- El reporte aparece como tarjeta de archivo HTML
- No repitas el contenido en tu respuesta
- Una frase breve de contexto o silencio
