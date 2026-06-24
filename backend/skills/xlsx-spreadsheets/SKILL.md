---
name: xlsx-spreadsheets
description: >-
  Create, read, or update Excel spreadsheets (.xlsx) in the chat. Use when the user
  mentions Excel, hoja de cálculo, spreadsheet, exportar datos, tabla descargable,
  or .xlsx — especially for tabular numeric data. Also use when updating an existing
  spreadsheet in the conversation. For narrative reports use docx-documents; for visual
  dashboards with charts use html-reports. Do NOT use for chat-only table answers
  that do not need a downloadable file.
---

# Hojas de cálculo Excel

## Resumen

Un `.xlsx` es un archivo tabular descargable. En Ayron usas las tools `create_spreadsheet`,
`update_spreadsheet` y `get_spreadsheet`. El backend construye el `.xlsx` con openpyxl
y lo muestra en el chat con vista previa estilo Excel.

## Cuándo usar

Activa esta skill cuando el usuario pida:

- Hoja Excel, spreadsheet o exportación tabular descargable
- Datos en columnas y filas para analizar o compartir fuera del chat
- Modificar una hoja ya generada en la conversación

No uses esta skill para:

- Respuestas cortas solo en el chat (`show_data_table` sin archivo)
- Informes narrativos con párrafos → `docx-documents`
- Dashboards visuales con gráficos → `html-reports`
- Fórmulas de Excel (`=SUM(...)`) — solo valores estáticos

## Tools de Ayron

| Tool | Uso |
|------|-----|
| `create_spreadsheet` | Crear una hoja nueva |
| `update_spreadsheet` | Modificar una hoja existente por `file_id` |
| `get_spreadsheet` | Leer el contenido estructurado antes de editar |
| `list_conversation_files` | Listar archivos de la conversación con sus `file_id` |

## Esquema de contenido

Pasa `title`, `filename` opcional y `sheets`. Cada hoja tiene `name`, `headers` y `rows`.

```json
{
  "title": "Desglose regional",
  "sheets": [
    {
      "name": "Revenue",
      "headers": ["Region", "Revenue", "Orders", "AOV", "MoM %"],
      "rows": [
        ["EMEA", {"value": "486,200", "align": "right"}, {"value": "5,632", "align": "right"}, {"value": "$86.32", "align": "right"}, {"value": "+18.2%", "tone": "success", "align": "right"}],
        {"style": "total", "cells": ["Total", {"value": "1,284,920", "align": "right"}, {"value": "15,209", "align": "right"}, {"value": "$84.48", "align": "right"}, {"value": "+12.4%", "tone": "success", "align": "right"}]}
      ]
    }
  ]
}
```

### Celdas enriquecidas

Cada celda puede ser un string o un objeto con:

- `value` — texto mostrado
- `align` — `left`, `right`, `center`
- `tone` — `success`, `danger`, `warning`, `muted`
- `bold` — `true` / `false`

### Filas con estilo

Las filas pueden ser listas simples o objetos con `style` (`total`, `subtotal`) y `cells`.

## Flujo recomendado

1. Consulta datos con SQL si hace falta.
2. Estructura una o más hojas con headers claros y filas alineadas.
3. Usa `tone` en columnas de variación o estado.
4. Marca la fila de totales con `"style": "total"`.
5. Llama `create_spreadsheet` y no repitas la tabla en el chat.

## Editar una hoja existente

1. Obtén el `file_id` del índice de archivos o con `list_conversation_files`.
2. Llama `get_spreadsheet(file_id)` para leer el contenido actual.
3. Llama `update_spreadsheet(file_id=..., sheets=...)` con el contenido actualizado.

## Límites

- Máximo 10 hojas por archivo
- Máximo 50 filas y 30 columnas por hoja
- Nombres de hoja: máximo 31 caracteres, sin `\ / * ? : [ ]`
