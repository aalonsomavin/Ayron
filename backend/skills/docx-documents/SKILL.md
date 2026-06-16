---
name: docx-documents
description: >-
  Create, read, edit, or export Word documents (.docx) in the chat. Use when the
  user mentions informe, memo, carta, plantilla, report, letter, resumen exportable,
  documento Word, or .docx — or asks for a polished written deliverable to download.
  Also use when updating an existing document in the conversation. For reports with
  charts, tables, or PDF export, use the html-reports skill instead. Do NOT use for PDFs,
  spreadsheets, Google Docs, or chat-only answers that do not need a downloadable file.
---

# Documentos Word

## Resumen

Un `.docx` es un archivo estructurado (ZIP + XML). En Ayron **no** generas ni editas XML,
docx-js ni scripts de unpack/pack: usas las tools `create_document`, `update_document`,
`get_document` y `list_conversation_files`. El backend construye el `.docx` con
python-docx y lo muestra en el chat con vista previa.

## Cuándo usar

Activa esta skill cuando el usuario pida:

- Informe, memo, carta, plantilla o resumen exportable
- Documento Word o archivo `.docx` descargable
- Modificar un documento ya generado en la conversación
- Reorganizar o ampliar contenido escrito en formato profesional

No uses esta skill para:

- Respuestas cortas solo en el chat
- Tablas o gráficos interactivos del chat (`show_data_table`, `show_chart`) — usa
  `html-reports` si el usuario quiere un informe exportable con esos elementos
- PDFs, Excel, Google Docs u otros formatos
- Edición XML, cambios rastreados, comentarios Word, imágenes incrustadas,
  índice (TOC), encabezados/pies de página o saltos de página — **no están soportados**
  por las tools actuales. Si el usuario los pide, explica la limitación y ofrece
  la mejor alternativa dentro del esquema soportado.

## Tools de Ayron

| Tool | Uso |
|------|-----|
| `create_document` | Crear un documento nuevo |
| `update_document` | Modificar un documento existente por `file_id` |
| `get_document` | Leer el contenido estructurado antes de editar |
| `list_conversation_files` | Listar documentos de la conversación con sus `file_id` |

El system prompt incluye un índice de archivos de la conversación con `file_id` cuando existen.

## Esquema de contenido

Pasa contenido estructurado con `title`, `subtitle`, `filename` opcional y `sections`.
Cada sección tiene un `heading` y contenido en `blocks` (recomendado) o en campos legacy
(`paragraphs`, `bullets`, `table`).

```json
{
  "title": "Informe de ventas",
  "subtitle": "Mayo 2026 · EMEA",
  "sections": [
    {
      "heading": "Resumen ejecutivo",
      "blocks": [
        {"type": "paragraph", "text": "Las ventas crecieron un 12 % respecto al mes anterior."},
        {"type": "callout", "variant": "info", "title": "Alcance", "text": "Datos de facturación Chinook, mayo 2026."},
        {"type": "separator"},
        {"type": "table", "headers": ["Región", "Ingresos"], "rows": [["EMEA", "$124.500"], ["LATAM", "$89.200"]]},
        {"type": "bullets", "items": ["Mayor crecimiento en EMEA", "LATAM estable"]},
        {"type": "callout", "variant": "warning", "text": "Los datos excluyen devoluciones pendientes."}
      ]
    }
  ]
}
```

### Tipos de block

| type | Campos | Uso |
|------|--------|-----|
| `paragraph` | `text` | Párrafo de cuerpo |
| `bullets` | `items` | Lista con viñetas |
| `table` | `headers`, `rows` | Tabla de datos |
| `separator` | — | Línea divisoria entre bloques |
| `callout` | `variant`, `text`, `title?` | Destacado visual |

Variantes de callout: `info`, `success`, `warning`, `danger`.

**Límites:** máx. 20 secciones, 40 blocks por sección, 50 filas por tabla, 8 callouts por sección.

**Estilo Ayron (aplicado automáticamente):** encabezado del documento con `title`
(descriptivo) y `subtitle` opcional, separador bajo el encabezado, footer con
«Generado con Ayron · fecha» y paginación «N de M», fuente Geist, tablas con encabezado gris y filas alternadas,
callouts con borde lateral de color y fondo suave, separadores hairline. El agente
no configura la marca manualmente.

## Flujo de trabajo

### Crear un documento nuevo

1. Si hace falta, consulta datos con SQL u otras tools.
2. Sintetiza el contenido en secciones claras (encabezados, párrafos, viñetas, tablas).
3. Llama `create_document` con `title`, `sections` y opcionalmente `subtitle` y `filename`.
4. Tras crear el documento, **no repitas su contenido** en el chat.

### Modificar un documento existente

1. Usa `list_conversation_files` o el índice de archivos del system prompt para obtener el `file_id`.
2. Si necesitas el contenido actual, llama `get_document(file_id)`.
3. Llama `update_document(file_id, ...)` con solo los campos que cambian.
4. **Nunca** llames `create_document` de nuevo para el mismo informe; usa `update_document`.
5. Tras actualizar, **no repitas el contenido** en el chat.

### Combinar con datos

Flujo típico: primero consulta datos (SQL, tablas, gráficos), luego sintetiza en el documento.
Los gráficos y tablas del chat no se incrustan automáticamente en el Word. Si el
usuario necesita gráficos o exportación PDF, usa la skill `html-reports` con
`create_html_report`. Para Word, resume los hallazgos en texto o tablas simples
dentro de `sections`.

## Calidad y formato

Principios adaptados para documentos profesionales generados con las tools de Ayron:

### Estructura

- **Título descriptivo** en `title` — nombre claro del documento (ej. «Informe de ventas EMEA — Mayo 2026», no «Informe»).
  Aparece como encabezado del documento con un separador debajo; no hace falta repetirlo en `sections`.
- **Contexto breve** en `subtitle` (fecha, alcance, destinatario, periodo).
- **Secciones con `heading` descriptivos** — una idea por sección (Resumen ejecutivo,
  Hallazgos, Recomendaciones, Anexos, etc.).
- Orden lógico: contexto → datos/hallazgos → conclusiones → próximos pasos.
- Para memos: Para / De / Fecha / Asunto puede ir en `subtitle` o en la primera sección.

### Párrafos, viñetas y blocks

- Prefiere `blocks` para controlar el orden exacto (párrafo → callout → tabla → separador).
- Párrafos concisos; evita bloques enormes.
- Usa `{"type": "bullets", "items": [...]}` — **nunca** insertes `•`, `-` o `\u2022` en párrafos.
- Usa `{"type": "separator"}` entre bloques temáticos dentro de una sección.
- Usa callouts para contexto (`info`), logros (`success`), advertencias (`warning`) o riesgos (`danger`).

### Tablas

- Siempre incluye `headers` con nombres legibles en español (no nombres SQL crudos).
- Alinea filas con el número de columnas de los encabezados.
- Formatea números, moneda y porcentajes en las celdas **antes** de enviar (ej. `$1.234,56`,
  `15,3 %`, `1.250 unidades`).
- Una tabla por sección cuando sea posible; no mezcles tablas gigantes con muchas columnas
  si un resumen en párrafos comunica mejor el mensaje.
- Para datos extensos: muestra un top-N en la tabla y menciona el total en un párrafo
  de la misma sección.

### Tipografía y tono

- Escribe en **español**, tono claro y profesional.
- El documento usa tipografía Geist alineada con Ayron; no intentes forzar fuentes manualmente.
- Usa comillas tipográficas cuando corresponda (« » o " ").

### Tipos de documento

| Tipo | Enfoque |
|------|---------|
| Informe | Resumen ejecutivo, metodología breve, hallazgos con tablas, conclusiones |
| Memo | Breve, directo; contexto + decisión o acción requerida |
| Carta | Saludo, cuerpo estructurado, cierre formal |
| Resumen exportable | Síntesis de datos ya analizados; tablas solo si aportan precisión |

## Reglas de presentación en el chat

- El documento aparece en el chat con vista previa; el usuario ya lo ve ahí.
- Prohibido volver a escribir el contenido del informe en tu mensaje de texto.
- Solo añade una frase breve si aporta contexto (ej. "Informe actualizado con los datos de mayo."),
  o termina sin texto.
- La tool devuelve `agent_instruction` confirmando que no debes repetir el contenido.
