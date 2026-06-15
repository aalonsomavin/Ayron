# Ayron — Plan técnico del proyecto

## 1. Visión general

Ayron es una plataforma multi-tenant de conversación con datos empresariales. Cada empresa conecta sus fuentes de datos, define roles y permisos para sus usuarios, y accede a un agente de IA capaz de analizar, generar y transformar información a través de un chat interactivo.

El agente se construye sobre **Deep Agents** (LangChain / LangGraph): un harness de agentes con planificación, sub-agentes, gestión de contexto, filesystem y skills extensibles. La plataforma orquesta ese agente por empresa, con aislamiento de datos, permisos granulares y ejecución en background para tareas largas o automatizadas.

---

## 2. Estado actual del repositorio

El proyecto parte de un template Django production-ready. Lo implementado hoy:

| Componente | Estado |
|---|---|
| Django 5.2 LTS | ✅ Base funcional |
| PostgreSQL | ✅ Configurado en Docker Compose |
| HTMX | ✅ Integrado vía CDN |
| TailwindCSS + daisyUI | ✅ Pipeline de build en Docker |
| Auth (login requerido) | ✅ Middleware + app `accounts` |
| Docker Compose (web + db + tailwind) | ✅ |
| pytest + ruff | ✅ |
| Deep Agents | ❌ Pendiente |
| Celery | ❌ Pendiente |
| Multi-tenancy (empresas) | ❌ Pendiente |
| Chat + streaming | ❌ Pendiente |
| Integraciones de datos | ❌ Pendiente |
| Skills / Automatizaciones | ❌ Pendiente |

### Estructura del monorepo

```
Ayron/
├── backend/                  # Django (API, templates, lógica de negocio)
│   ├── config/settings/      # base, dev, test, prod
│   ├── apps/
│   │   ├── core/             # Home, middleware, health
│   │   └── accounts/         # Login/logout
│   ├── templates/
│   └── static/
├── frontend/                 # Tailwind + daisyUI (CSS only)
├── docker/
├── scripts/
└── compose.yml
```

---

## 3. Stack tecnológico

### Backend

| Tecnología | Rol |
|---|---|
| **Django 5.2** | Framework web, ORM, auth, admin, templates |
| **PostgreSQL 16** | Base de datos principal (multi-tenant, conversaciones, integraciones, skills) |
| **Deep Agents** (`deepagents`) | Harness del agente IA sobre LangGraph |
| **LangChain / LangGraph** | Runtime del agente: streaming, persistencia, tool-calling |
| **Celery** | Ejecución en background de llamadas al agente y automatizaciones |
| **Redis** (broker Celery + cache/streaming) | Cola de tareas y pub/sub para eventos en tiempo real |
| **django-environ** | Configuración por variables de entorno |

### Frontend

| Tecnología | Rol |
|---|---|
| **HTMX** | Interacciones dinámicas sin SPA; partials del servidor |
| **TailwindCSS + daisyUI** | Estilos y componentes UI |
| **SSE o polling HTMX** | Consumo de eventos del agente mientras procesa |

### Infraestructura

| Tecnología | Rol |
|---|---|
| **Docker Compose** | Entorno de desarrollo (web, db, tailwind, celery, redis) |
| **S3-compatible storage** (prod) | Archivos subidos, documentos generados por el agente |
| **pytest + pytest-django** | Tests |
| **ruff** | Linting y formateo |

---

## 4. Arquitectura de alto nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                         Cliente (Browser)                       │
│              HTMX + Tailwind/daisyUI + SSE/polling              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼────────────────────────────────────┐
│                      Django (ASGI/WSGI)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ accounts │ │ companies│ │   chat   │ │  integrations    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  skills  │ │automations│ │  files  │ │  permissions     │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────┐                                                   │
│  │  memory  │  Memoria persistente por usuario                  │
│  └──────────┘                                                   │
└────────┬───────────────────────────────┬────────────────────────┘
         │                               │
         ▼                               ▼
┌─────────────────┐            ┌─────────────────────┐
│   PostgreSQL    │            │       Redis         │
│  (datos + state)│            │ (Celery + eventos)  │
└─────────────────┘            └──────────┬──────────┘
                                          │
                               ┌──────────▼──────────┐
                               │   Celery Workers    │
                               │  (agente + cron)    │
                               └──────────┬──────────┘
                                          │
                               ┌──────────▼──────────┐
                               │    Deep Agent       │
                               │  (LangGraph runtime)│
                               └──────────┬──────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
            Integraciones           LLM Provider          File Storage
            (APIs, DBs, etc.)      (OpenAI, Anthropic…)    (S3 / local)
```

### Principios de diseño

1. **Multi-tenancy por empresa**: todo dato de negocio está scoped a `Company`. Un usuario pertenece a una empresa.
2. **Permisos basados en roles**: cada empresa define roles con permisos granulares (ver datos, usar agente, administrar integraciones, etc.).
3. **Agente aislado por contexto**: el Deep Agent recibe solo las tools e integraciones que el rol del usuario permite.
4. **Ejecución async por defecto**: las conversaciones con el agente corren en Celery; el front consume eventos en streaming.
5. **Server-rendered first**: HTMX para la mayoría de la UI; mínima lógica en el cliente.

---

## 5. Modelo de dominio

### 5.1 Empresa (`Company`)

Entidad raíz del tenant. Agrupa usuarios, integraciones, skills, automatizaciones y conversaciones.

```
Company
├── id (UUID)
├── name
├── slug
├── settings (JSON)          # config general: LLM preferido, límites, etc.
├── is_active
├── created_at / updated_at
```

### 5.2 Usuario (`User`)

Se extiende el modelo base de Django (`AbstractUser`) como `AUTH_USER_MODEL`. El login usa `email` como identificador único (`USERNAME_FIELD = "email"`).

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT)
    role = models.ForeignKey("permissions.Role", on_delete=models.PROTECT)
    is_company_admin = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
```

```
User (AbstractUser)
├── id
├── email (unique, USERNAME_FIELD)
├── password
├── first_name / last_name
├── is_active / is_staff / is_superuser
├── company_id → Company
├── role_id → Role
├── is_company_admin
├── date_joined / last_login
```

**Configuración Django:**

```python
# settings/base.py
AUTH_USER_MODEL = "accounts.User"
```

**Implicaciones:**

- Migraciones iniciales deben definir `User` antes que cualquier FK a usuario.
- `django.contrib.auth` sigue funcionando: login, sesiones, permisos Django (`is_staff`, `is_superuser`).
- Los permisos de negocio (agente, skills, integraciones) viven en `Role`, no en `user_permissions` de Django.
- Superusers (`is_superuser`) bypass tenant para admin interno; usuarios normales siempre scoped a su `company`.

### 5.3 Roles y permisos (`Role`, `Permission`)

Cada empresa crea sus propios roles. Los permisos son flags o codenames reutilizables.

**Permisos previstos (ejemplos):**

| Codename | Descripción |
|---|---|
| `agent.use` | Puede iniciar conversaciones con el agente |
| `agent.view_history` | Puede ver conversaciones propias o del equipo |
| `integrations.view` | Puede ver integraciones configuradas |
| `integrations.manage` | Puede crear/editar/eliminar integraciones |
| `skills.view` | Puede ver skills de la empresa |
| `skills.manage` | Puede crear/editar skills manualmente |
| `skills.propose` | El agente puede proponerle modificaciones a skills (requiere también acceso al skill concreto) |
| `automations.view` | Puede ver automatizaciones |
| `automations.manage` | Puede crear/editar automatizaciones |
| `files.upload` | Puede subir archivos al chat |
| `files.download` | Puede descargar archivos generados |
| `users.manage` | Puede administrar usuarios y roles |
| `company.settings` | Puede editar configuración de la empresa |

```
Role
├── id
├── company_id → Company
├── name
├── permissions (M2M → Permission)
├── is_default

Permission
├── codename (unique)
├── description
```

### 5.4 Integraciones de datos (`Integration`)

Cada empresa configura N integraciones que exponen datos al agente como tools de LangChain / MCP.

```
Integration
├── id
├── company_id → Company
├── name
├── type                     # postgres, rest_api, google_sheets, s3, etc.
├── config (JSON, encrypted) # credenciales, endpoints, queries
├── schema_cache (JSON)      # metadata descubierta (tablas, campos)
├── is_active
├── created_by → User
├── created_at / updated_at
```

**Flujo de integración:**

1. Admin de empresa configura la integración (tipo + credenciales).
2. El sistema valida la conexión y descubre schema/metadata.
3. Se generan tools dinámicas que el Deep Agent puede invocar.
4. El acceso a cada integración se filtra por rol del usuario.

### 5.5 Skills (`Skill`)

Habilidades personalizadas por empresa que extienden el comportamiento del agente. Un skill es esencialmente un prompt/instrucción + tools asociadas + metadata.

```
Skill
├── id
├── company_id → Company
├── name
├── description
├── instructions (text)      # system prompt parcial o reglas de comportamiento
├── tools (JSON)             # subset de tools permitidas
├── version
├── is_active
├── created_by → User
├── created_at / updated_at
```

**Aprendizaje en conversación:** al finalizar una conversación, el agente puede proponer una modificación a un skill existente (ej. nueva regla de formato, nuevo paso en un workflow). El usuario aprueba o rechaza; si aprueba, se crea una nueva versión del skill.

**Restricción de permisos:** el agente solo puede proponer modificaciones a skills que el usuario tenga permiso de modificar. En runtime se calcula un allowlist:

1. Usuario tiene permiso `skills.propose` (o `skills.manage`) en su rol.
2. El skill pertenece a la empresa del usuario.
3. Opcionalmente, el skill está en un subset explícito del rol (si se implementa restricción por skill).

Si no hay skills elegibles, la tool `propose_skill_revision` no se incluye en el agente y cualquier intento del LLM se rechaza en el backend.

```
SkillRevision
├── id
├── skill_id → Skill
├── proposed_by              # agent | user
├── diff (JSON)              # cambios propuestos
├── status                   # pending | approved | rejected
├── conversation_id → Conversation
├── reviewed_by → User
├── created_at
```

### 5.6 Conversaciones (`Conversation`, `Message`)

```
Conversation
├── id (UUID)
├── company_id → Company
├── user_id → User
├── title
├── status                   # active | processing | completed | failed
├── celery_task_id
├── metadata (JSON)
├── created_at / updated_at

Message
├── id
├── conversation_id → Conversation
├── role                     # user | assistant | system | tool
├── content (text)
├── attachments (M2M → File)
├── tool_calls (JSON)
├── created_at

AgentEvent
├── id
├── conversation_id → Conversation
├── message_id → Message (nullable)   # agrupa eventos de una misma ejecución/turno
├── event_type               # token | tool_start | tool_end | plan | error | done | ...
├── payload (JSON)
├── sequence_number          # monótono por conversation_id; source of truth para replay
├── created_at
```

**Índice:** `(conversation_id, sequence_number)` unique — garantiza orden total y replay sin gaps.

**Ciclo por turno:** cada mensaje del usuario dispara una ejecución del agente. Al encolar la task:

1. Se crea `Message` (role=`user`).
2. Se crea `Message` vacío (role=`assistant`, status=`streaming`) como `active_message_id`.
3. `Conversation.status` pasa a `processing`.
4. Todos los `AgentEvent` del turno llevan ese `message_id`.
5. Al evento `done`, se consolida el contenido final en el `Message` assistant y `Conversation.status` vuelve a `active` (o `completed` si aplica).

Esto permite replay granular por turno y reconstrucción correcta al recargar mid-flight.

### 5.6.1 Memoria del usuario (`UserMemory`)

Memoria persistente cross-conversación scoped al par `(company, user)`. El agente puede leer y escribir hechos aprendidos durante conversaciones (preferencias, contexto recurrente, definiciones internas, etc.).

```
UserMemory
├── id
├── company_id → Company
├── user_id → User
├── key                        # slug corto, ej. "reporte_mensual_formato"
├── content (text)             # el hecho o instrucción persistida
├── source_conversation_id → Conversation (nullable)
├── source_message_id → Message (nullable)
├── created_by                 # agent | user
├── is_active
├── created_at / updated_at
```

**Comportamiento:**

- Al iniciar una conversación, el agente recibe en el system prompt un resumen de las entradas activas de `UserMemory` del usuario.
- Tools dedicadas:
  - `read_user_memory` — lista/busca entradas activas del usuario.
  - `write_user_memory` — crea o actualiza una entrada (siempre scoped a `company + user` de la sesión).
  - `delete_user_memory` — soft-delete (`is_active=False`); solo el agente o el usuario desde settings.
- El usuario puede ver/editar/eliminar su memoria desde `/settings/memory/`.
- Límites configurables por empresa: max entradas, max chars por entrada.

**Diferencia con skills:**

| | Skill | UserMemory |
|---|---|---|
| Scope | Empresa (compartido) | Usuario dentro de la empresa |
| Quién edita | Admins / propuesta del agente con aprobación | Agente en conversación + usuario |
| Propósito | Comportamiento reutilizable del agente | Contexto personal aprendido en chats |

### 5.7 Archivos (`File`)

```
File
├── id
├── company_id → Company
├── uploaded_by → User
├── conversation_id → Conversation (nullable)
├── original_name
├── mime_type
├── size_bytes
├── storage_path             # S3 key o path local
├── parsed_content (text)    # texto extraído para el agente
├── created_at
```

**Formatos soportados:**

| Tipo | Lectura | Generación |
|---|---|---|
| Excel (.xlsx, .xls) | ✅ | ✅ |
| Word (.docx) | ✅ | ✅ |
| PDF | ✅ | ❌ |
| Imágenes (png, jpg, webp) | ✅ (visión LLM) | ❌ |

### 5.8 Automatizaciones (`Automation`)

Ejecución recurrente del agente con una consulta fija.

```
Automation
├── id
├── company_id → Company
├── name
├── prompt (text)            # consulta que se envía al agente
├── schedule (cron expr)     # ej. "0 8 * * 1" = lunes 8am
├── skills (M2M → Skill)     # skills activas para esta automatización
├── integrations (M2M)       # integraciones disponibles
├── notify_users (M2M → User)
├── is_active
├── last_run_at
├── next_run_at
├── created_by → User
```

```
AutomationRun
├── id
├── automation_id → Automation
├── celery_task_id
├── status                   # pending | running | completed | failed
├── result_summary (text)
├── conversation_id → Conversation
├── started_at / finished_at
```

---

## 6. Agente de IA (Deep Agents)

### 6.1 Qué es Deep Agents

[Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) es un harness de agentes construido sobre LangChain y LangGraph. Incluye out-of-the-box:

- **Planificación** (`write_todos`): descomposición de tareas multi-paso.
- **Filesystem** (`read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`): memoria de trabajo y gestión de contexto largo.
- **Sub-agentes** (`task`): delegación con contexto aislado.
- **Skills**: instrucciones reutilizables inyectables al agente.
- **Streaming**: eventos tipados (mensajes, tool calls, sub-agentes).
- **MCP**: conexión a servidores Model Context Protocol para tools externas.

### 6.2 Integración con Ayron

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=company.settings["llm_model"],
    tools=build_company_tools(company, user.role),
    skills=load_company_skills(company),
    system_prompt=build_system_prompt(company, user),
)
```

**Construcción dinámica de tools por sesión:**

1. Se cargan las integraciones activas de la empresa a las que el rol tiene acceso.
2. Cada integración se traduce a una o más LangChain tools (query SQL, REST call, etc.).
3. Se agregan tools de filesystem para leer/escribir archivos de la conversación.
4. Se inyectan los skills aprobados de la empresa como instrucciones parciales.
5. Se agregan tools de memoria del usuario (`read_user_memory`, `write_user_memory`).
6. Se agrega `search_past_conversations` si el rol tiene `agent.view_history`.
7. Se agrega `propose_skill_revision` solo si el rol tiene `skills.propose`/`skills.manage` y existe al menos un skill elegible.

**Tool: `search_past_conversations`**

Permite al agente buscar en conversaciones anteriores del usuario (o del equipo, según permisos).

```python
def search_past_conversations(
    query: str,
    limit: int = 10,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[ConversationSearchResult]:
    ...
```

**Scope de búsqueda según permisos:**

| Permiso | Alcance |
|---|---|
| Solo `agent.use` | Conversaciones propias del usuario |
| `agent.view_history` | Conversaciones de toda la empresa (filtradas por `company_id`) |

**Implementación de búsqueda:**

- Full-text search en PostgreSQL sobre `Message.content` + `Conversation.title` (`SearchVector` / GIN index).
- Resultados: `{conversation_id, title, snippet, message_date, relevance}`.
- El agente usa esto para recuperar contexto de chats previos sin cargar todo el historial en el prompt.
- Índice: `(company_id, user_id, created_at)` en `Conversation`; GIN en contenido de mensajes.

### 6.3 Flujo de una conversación

```
Usuario escribe mensaje (+ archivos opcionales)
        │
        ▼
Django crea Message + encola Celery task
        │
        ▼
Celery worker instancia Deep Agent con contexto de empresa/usuario
        │
        ▼
Agent.stream() emite eventos
        ├─→ Persiste cada evento en AgentEvent (Postgres, sequence_number++)
        └─→ Publica en Redis pub/sub (canal: conversation:{id}) para clientes conectados
        │
        ▼
Django SSE endpoint / HTMX polling entrega eventos → actualiza UI
        │
        ▼
Al finalizar: persiste Message assistant, archivos generados,
             propuesta de skill (solo skills elegibles), escrituras a UserMemory
```

### 6.4 Generación de documentos

El agente usa las tools de filesystem de Deep Agents para crear archivos en un directorio temporal scoped a la conversación. Al terminar:

1. Los archivos generados (.xlsx, .docx) se suben a object storage.
2. Se crean registros `File` vinculados a la conversación.
3. El front muestra links de descarga vía HTMX partial.

### 6.5 Propuesta de modificación de skills

Al detectar un patrón repetible o una mejora en la conversación, el agente puede invocar `propose_skill_revision(skill_id, diff)` **solo sobre skills incluidos en el allowlist del usuario** (ver §5.5). Si el `skill_id` no es elegible, la tool retorna error y no se emite evento.

Flujo:

1. Backend valida permisos + pertenencia del skill a la empresa.
2. Se crea `SkillRevision` en status `pending`.
3. Se emite evento `skill_proposal` en el stream.
4. La UI muestra un modal (daisyUI) para aprobar/rechazar.
5. Si se aprueba, se activa la nueva versión del skill.

### 6.6 Memoria del usuario en conversación

Al construir el agente para una sesión:

1. Se cargan entradas activas de `UserMemory` del usuario.
2. Se inyectan en el system prompt como bloque compacto.
3. Durante la conversación, el agente puede llamar `write_user_memory` cuando aprende algo reutilizable (ej. "el usuario prefiere reportes en Excel con columna de fecha primero").
4. Cada escritura genera evento `memory_updated` en el stream (opcional en UI: toast discreto).

---

## 7. Capa de streaming de eventos

El front necesita ver en tiempo real lo que hace el agente (tokens, invocación de tools, planificación, errores). Además, **al recargar la página** debe reconstruir el estado completo: todos los eventos pasados de la ejecución actual y de ejecuciones anteriores, más los eventos nuevos si el agente sigue corriendo.

### Principio: Postgres como source of truth, Redis como fan-out

| Capa | Rol |
|---|---|
| **`AgentEvent` (Postgres)** | Persistencia durable, replay al recargar, auditoría |
| **Redis pub/sub** | Entrega en tiempo real a clientes ya conectados |

Cada evento se escribe primero en Postgres (con `sequence_number` asignado) y luego se publica a Redis. Nunca confiar solo en Redis para reconstruir estado.

### Carga inicial al abrir/recargar un chat

```
GET /chat/{conversation_id}/
```

La vista renderiza:

1. **Mensajes** (`Message`) — burbujas user/assistant ya finalizadas.
2. **Timeline de la ejecución en curso** (si `status=processing`) — reconstruida desde `AgentEvent` del turno activo.
3. **Metadata de conexión** — `last_sequence`, `status`, `active_message_id` embebidos en el HTML para el cliente.

```
GET /chat/{conversation_id}/events/?after={sequence}
```

- Sin `after`: retorna **todos** los eventos de la conversación (paginado si > N, pero el cliente itera hasta completar).
- Con `after`: retorna eventos con `sequence_number > after` (catch-up + live).

Respuesta:

```json
{
  "events": [
    {"seq": 1, "type": "plan", "payload": {...}, "message_id": "..."},
    {"seq": 2, "type": "tool_start", "payload": {...}, "message_id": "..."}
  ],
  "last_sequence": 42,
  "status": "processing",
  "has_more": false
}
```

### Flujo de recarga (100% de eventos)

```
Usuario recarga /chat/{id}/
        │
        ▼
Server renderiza mensajes completos + estado (status, last_sequence)
        │
        ▼
Cliente JS pide GET /events/?after=0  (o after=last_rendered_seq)
        │
        ▼
Replay de TODOS los AgentEvent en orden → reconstruye UI
  (tokens, tools, plans, files, proposals, errors)
        │
        ▼
Si status == "processing":
  abre SSE GET /stream/?after={last_sequence}
  solo recibe eventos nuevos (seq > last_sequence)
        │
        ▼
Si status == "completed":
  no abre SSE; UI ya refleja estado final
```

**Garantías:**

- **Sin pérdida:** todo evento emitido por el worker existe en `AgentEvent` antes de publicarse a Redis.
- **Orden total:** el cliente aplica eventos estrictamente por `sequence_number` ascendente.
- **Idempotencia:** el cliente trackea `lastAppliedSeq`; ignora duplicados si replay y SSE se solapan.
- **Ejecución en curso:** al recargar mid-flight, el replay muestra exactamente lo ya ocurrido; SSE continúa desde el último seq.
- **Ejecución terminada:** al recargar post-`done`, el replay reconstruye la ejecución completa idéntica a si el usuario hubiera estado conectado.

### SSE en vivo (solo eventos nuevos)

```
GET /chat/{conversation_id}/stream/?after=42
Content-Type: text/event-stream

event: token
data: {"seq": 43, "content": "Analizando"}

event: tool_start
data: {"seq": 44, "tool": "query_sales_db", "input": {"year": 2025}}

event: done
data: {"seq": 58, "message_id": "uuid"}
```

**Implementación:**

1. Celery worker: `INSERT AgentEvent` → `PUBLISH conversation:{id}` con payload incluyendo `seq`.
2. Vista ASGI SSE: suscrita a Redis, filtra `seq > after`, emite al cliente.
3. Cliente: listener JS mínimo (no depender de SSE para replay histórico).
4. Fallback: polling HTMX `GET /events/?after={seq}` cada 1–2s si SSE falla.

### Reconstrucción de UI por tipo de evento (replay)

| Evento | Replay en recarga |
|---|---|
| `token` | Concatena en el bubble assistant del turno (`message_id`) |
| `plan` | Renderiza/actualiza checklist de todos |
| `tool_start` / `tool_end` | Renderiza cards de tool invocada |
| `file_created` | Muestra link de descarga |
| `skill_proposal` | Muestra modal/badge pendiente de revisión |
| `memory_updated` | Opcional: indicador de memoria actualizada |
| `error` | Banner de error |
| `done` | Cierra turno, habilita input |

### Eventos tipados

| Evento | Cuándo | Payload |
|---|---|---|
| `token` | Streaming de texto del assistant | `{seq, content, message_id}` |
| `plan` | Agente crea/actualiza todos | `{seq, todos, message_id}` |
| `tool_start` | Inicio de invocación de tool | `{seq, tool, input, message_id}` |
| `tool_end` | Fin de invocación | `{seq, tool, output_summary, message_id}` |
| `file_created` | Agente generó un archivo | `{seq, file_id, name, mime, message_id}` |
| `skill_proposal` | Propuesta de modificar skill | `{seq, skill_id, diff, revision_id, message_id}` |
| `memory_updated` | Agente escribió memoria | `{seq, memory_id, key, message_id}` |
| `error` | Error recuperable o fatal | `{seq, message, recoverable, message_id}` |
| `done` | Turno del agente terminado | `{seq, message_id}` |

---

## 8. Celery y automatizaciones

### Servicios adicionales en Docker Compose

```yaml
redis:
  image: redis:7-alpine

celery-worker:
  build: docker/backend/Dockerfile
  command: celery -A config worker -l info
  depends_on: [db, redis]

celery-beat:
  build: docker/backend/Dockerfile
  command: celery -A config beat -l info
  depends_on: [db, redis]
```

### Tareas Celery

| Task | Trigger | Descripción |
|---|---|---|
| `run_agent_conversation` | Usuario envía mensaje | Ejecuta el Deep Agent y publica eventos |
| `run_automation` | Celery Beat (cron) | Ejecuta automatización programada |
| `parse_uploaded_file` | Upload de archivo | Extrae texto/contenido del archivo |
| `sync_integration_schema` | Creación/edición de integración | Descubre schema de la fuente de datos |
| `process_skill_revision` | Aprobación de skill | Activa nueva versión del skill |

### Automatizaciones

1. Admin crea automatización con prompt + schedule cron + skills/integraciones.
2. Celery Beat evalúa `Automation.next_run_at` y encola `run_automation`.
3. El worker ejecuta el agente igual que una conversación, pero sin usuario interactuando.
4. Resultado se guarda en `AutomationRun` y se notifica a `notify_users` (email o in-app).

---

## 9. Frontend (HTMX + daisyUI)

### Pantallas principales

| Ruta | Descripción |
|---|---|
| `/` | Dashboard: conversaciones recientes, automatizaciones, accesos rápidos |
| `/chat/` | Lista de conversaciones |
| `/chat/new/` | Nueva conversación |
| `/chat/{id}/` | Chat con streaming, drag & drop de archivos |
| `/integrations/` | CRUD de integraciones de datos |
| `/skills/` | CRUD de skills + revisiones pendientes |
| `/automations/` | CRUD de automatizaciones + historial de runs |
| `/settings/roles/` | Gestión de roles y permisos |
| `/settings/users/` | Gestión de usuarios de la empresa |
| `/settings/company/` | Config general de la empresa |
| `/settings/memory/` | Ver/editar memoria persistente del usuario |

### Patrones HTMX

- **Chat input**: `hx-post` envía mensaje → retorna partial vacío + trigger conexión live.
- **Carga inicial / recarga**: JS fetch de `/events/?after=0` → replay completo → luego SSE si `processing`.
- **Streaming live**: SSE (o polling fallback) append solo eventos con `seq > lastAppliedSeq`.
- **File upload**: `hx-post` con `hx-encoding="multipart/form-data"` al drop zone.
- **Modals**: daisyUI `<dialog>` para aprobar skill revisions, confirmar acciones.
- **Lists**: paginación con `hx-get` + partials para integraciones, skills, etc.

### Componentes daisyUI clave

- `chat` / custom message bubbles para el hilo de conversación.
- `file-input` + drop zone para uploads.
- `table` + `badge` para integraciones y automatizaciones.
- `modal` para propuestas de skills.
- `timeline` para historial de automation runs.
- `navbar` + `drawer` para navegación lateral.

---

## 10. Seguridad

| Área | Medida |
|---|---|
| Multi-tenancy | Todas las queries filtradas por `company_id`; middleware de tenant |
| Credenciales de integraciones | Encriptadas at-rest (django-fernet-fields o similar) |
| Roles | Permiso check en views y en construcción de tools del agente |
| Skill proposals | Allowlist por usuario; validación server-side en tool y en aprobación |
| UserMemory | Scoped a `(company, user)`; agente no puede escribir memoria de otro usuario |
| Conversation search | Scope propio vs empresa según `agent.view_history` |
| Archivos | Storage scoped por empresa; signed URLs para descarga |
| CSRF | Protección Django estándar en forms HTMX |
| Rate limiting | Por usuario/empresa en endpoints del agente |
| LLM | API keys a nivel de plataforma o por empresa (configurable) |

---

## 11. Apps Django planificadas

```
backend/apps/
├── core/           # ✅ Home, middleware, health
├── accounts/       # ✅ Auth → User(AbstractUser), login por email
├── companies/      # Company, settings, tenant middleware
├── permissions/    # Role, Permission, decorators
├── integrations/   # Integration CRUD + tool builders
├── skills/         # Skill, SkillRevision, allowlist por usuario
├── memory/         # UserMemory, CRUD + tools del agente
├── chat/           # Conversation, Message, AgentEvent, replay + SSE views
├── files/          # Upload, parsing, storage
├── automations/    # Automation, AutomationRun, Celery Beat
└── agent/          # Deep Agent wrapper, tool factory, streaming
```

---

## 12. Variables de entorno (extensión de `.env.example`)

```env
# Django
DEBUG=1
SECRET_KEY=change-me-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://django:django@localhost:5432/django

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# LLM
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
DEFAULT_LLM_MODEL=openai:gpt-4o

# Storage
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=

# Encryption
FIELD_ENCRYPTION_KEY=
```

---

## 13. Fases de implementación

### Fase 1 — Fundamentos multi-tenant
- [ ] `User(AbstractUser)` con email login + `AUTH_USER_MODEL`
- [ ] Modelos `Company`, `Role`, `Permission`
- [ ] Tenant middleware (scoped queries por empresa)
- [ ] CRUD de usuarios y roles por empresa
- [ ] Admin Django para gestión interna

### Fase 2 — Chat básico con agente
- [ ] Integrar `deepagents` + configuración LLM
- [ ] Modelos `Conversation`, `Message`, `AgentEvent` (con `sequence_number` + `message_id`)
- [ ] Celery + Redis en Docker Compose
- [ ] Task `run_agent_conversation` (persist-then-publish)
- [ ] Endpoint `GET /events/` para replay completo
- [ ] Endpoint SSE `/stream/?after=` para eventos nuevos
- [ ] UI de chat: replay al recargar + live streaming sin gaps

### Fase 3 — Archivos
- [ ] Upload drag & drop en chat
- [ ] Parsing de Excel, Word, PDF, imágenes
- [ ] Generación de Excel/Word por el agente
- [ ] Storage (local dev → S3 prod)

### Fase 4 — Integraciones de datos
- [ ] Modelo `Integration` + CRUD
- [ ] Conectores iniciales (PostgreSQL, REST API)
- [ ] Tool factory dinámica por integración
- [ ] Filtrado de tools por rol

### Fase 5 — Skills, memoria y búsqueda
- [ ] Modelo `Skill` + CRUD
- [ ] Inyección de skills al agente
- [ ] Propuesta de revisiones con allowlist por permisos (`skills.propose`)
- [ ] Modelo `UserMemory` + tools read/write + UI settings
- [ ] Tool `search_past_conversations` + índices full-text en Postgres

### Fase 6 — Automatizaciones
- [ ] Modelo `Automation` + CRUD
- [ ] Celery Beat + scheduling cron
- [ ] Historial de runs + notificaciones

### Fase 7 — Producción
- [ ] Settings prod, HTTPS, S3
- [ ] Rate limiting, monitoring, logging estructurado
- [ ] Tests de integración end-to-end
- [ ] CI/CD pipeline

---

## 14. Decisiones técnicas abiertas

| Decisión | Opciones | Notas |
|---|---|---|
| SSE vs WebSockets | SSE (recomendado) vs Django Channels | SSE es más simple con HTMX; WS si se necesita bidireccional |
| Storage de archivos | Local (dev) / S3 (prod) | django-storages |
| Encriptación de credenciales | django-fernet-fields vs vault externo | Fernet suficiente para MVP |
| LLM provider | OpenAI / Anthropic / multi | Deep Agents es model-agnostic |
| Conectores de integración | Custom vs MCP servers | MCP alinea con Deep Agents nativamente |
| Auth futuro | Django auth vs SSO (SAML/OIDC) | Django auth para MVP; SSO en fase enterprise |

---

## 15. Referencias

- [Deep Agents — LangChain Docs](https://docs.langchain.com/oss/python/deepagents/overview)
- [Deep Agents GitHub](https://github.com/langchain-ai/deepagents)
- [LangGraph Streaming](https://docs.langchain.com/oss/python/langgraph/streaming)
- [HTMX SSE Extension](https://htmx.org/extensions/sse/)
- [daisyUI Components](https://daisyui.com/components/)
- [Celery + Django](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
