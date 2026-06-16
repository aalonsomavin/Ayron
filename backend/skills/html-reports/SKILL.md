---
name: html-reports
description: >-
  Create, read, edit, or export HTML reports in the chat. Use for data reports,
  concept explainers, status updates, incident reports, technical briefs, learning
  syntheses, and any deliverable meant for a human to read and share — exportable
  as PDF. The agent writes semantic HTML directly. Do NOT use for Word (.docx) or
  chat-only answers. Also use when updating an existing HTML report.
---

# Reportes HTML — research, informes y aprendizaje

## Por qué HTML

Los reportes HTML se **leen**; un markdown del mismo tamaño en el chat, no. Usa esta skill
cuando el objetivo es que alguien **absorba información**: explainers, status, postmortems,
briefs técnicos, dashboards, síntesis de código o datos.

## Cuándo usar

- Informe con tablas, gráficos SVG, diagramas o visualizaciones
- Exportación a PDF
- «Resume cómo funciona X» / «Explícame el sistema Y»
- Postmortem, status semanal, brief técnico
- Objetivo de **comprensión o compartir**, no implementación inmediata

No uses para: Word (`.docx`), respuestas solo en chat, tablas/gráficos sueltos (`show_data_table`, `show_chart`).

## Tools

| Tool | Uso |
|------|-----|
| `create_html_report` | Crear reporte — pasas **`html`** (markup) |
| `update_html_report` | Actualizar por `file_id` — pasas `html` nuevo si cambia el contenido |
| `get_html_report` | Leer el `html` actual antes de editar |
| `list_conversation_files` | Listar archivos con `file_id` |

**No uses JSON de sections/blocks.** Escribe HTML semántico; Ayron lo sanitiza, guarda y exporta.

## Cómo pasar el HTML

```python
create_html_report(
    title="Rate limiter — explicación",
    subtitle="Cómo funciona el token bucket en Ayron",
    filename="rate-limiter-explicacion.html",
    html=\"\"\"
<style>
  :root { --ink: #18181b; --muted: #62626b; --border: #e6e6e8; }
  body { font-family: Georgia, serif; color: var(--ink); max-width: 720px; margin: 0 auto; padding: 2rem; }
  h1 { font-size: 1.75rem; letter-spacing: -0.02em; }
  .tldr { background: #fafafa; border-left: 4px solid #3b6ef6; padding: 1rem; margin: 1.5rem 0; }
  table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
  th, td { border: 1px solid var(--border); padding: 0.5rem 0.75rem; text-align: left; }
  pre { background: #f4f4f5; padding: 1rem; overflow-x: auto; font-size: 0.85rem; }
  @media (max-width: 700px) { body { padding: 1rem; } }
  @media print { body { max-width: none; } }
</style>
<header>
  <h1>Rate limiter</h1>
  <p class="lead">Token bucket por IP — una lectura.</p>
</header>
<section class="tldr"><strong>TL;DR</strong> — Cada IP tiene un bucket; cada request consume un token.</section>
<section>
  <h2>Flujo</h2>
  <svg viewBox="0 0 400 120" width="100%" height="120" role="img">...</svg>
</section>
<section>
  <h2>Código clave</h2>
  <pre><code>def allow(ip): ...</code></pre>
</section>
<section>
  <h2>Gotchas</h2>
  <ul><li>El bucket no persiste entre reinicios.</li></ul>
</section>
<footer><h2>Fuentes</h2><ul><li>middleware/rate_limit.py</li></ul></footer>
\"\"\",
)
```

Puedes pasar un **fragmento** (como arriba) o un documento completo (`<!DOCTYPE html>...`).
Ayron añade footer con fecha en export/PDF si falta.

## Requisitos del HTML

- **Autocontenido:** CSS en `<style>` inline; Google Fonts vía `<link>` permitido
- **Semántico:** `<table>` para datos, `<pre><code>` para código, `<svg>` para diagramas
- **Sin JS:** no `<script>` — export y PDF son estáticos
- **Responsive:** usable en móvil (~700px) y en PDF (print CSS)
- **Una lectura:** TL;DR arriba, secciones escaneables, **Fuentes** al final
- **`filename` descriptivo:** `<tema>-<tipo>.html`

## Estructura recomendada

TL;DR → Contexto → Contenido principal → Diagramas/datos → Gotchas → Próximos pasos → Fuentes

## Patrones

| Patrón | Cuándo | Enfoque |
|--------|--------|---------|
| A Explicador | «Cómo funciona X» | TL;DR + SVG de flujo + snippets + gotchas |
| B Status | «Qué entregamos esta semana» | Secciones por área, tablas con cifras, bullets |
| C Incidente | Postmortem | Timeline en tabla, callouts visuales, action items |
| D Deep-dive | Aprendizaje | 5–10 secciones, mezcla prosa + tablas + SVG |
| E Decisión | «¿Hacemos X?» | Recomendación primero, alternativas después |

## Sintetizar fuentes

Cita en prosa: «(middleware/rate_limit.py)», «(consulta SQL: ventas por región)».
Lista completa en sección **Fuentes**.

## Anti-patrones

- Volcar el informe en markdown en el chat
- JSON de blocks en lugar de HTML
- `<script>` o handlers inline (`onclick`)
- Repetir fuentes sin sintetizar
- Informe sin «qué sigue» o fuentes

## Flujo

1. Investiga (SQL, contexto, etc.)
2. Escribe HTML completo con estilo deliberado (no generic AI slop)
3. `create_html_report(title, html, subtitle, filename)`
4. No repitas contenido en el chat

Para editar: `get_html_report` → modifica `html` → `update_html_report(file_id, html=...)`

## Reglas en el chat

- El reporte aparece como tarjeta de archivo HTML
- No repitas el contenido en tu respuesta
- Una frase breve de contexto o silencio
