# HERMES - RECOVERY AUDIT

Fecha: 2026-05-20
Modo: local primero, sin cloud, sin runner nuevo, sin provider real.

## ACTUALIZACION FASE C - RECOVERY IA LOCAL

- `/ai/test` ahora usa `app.ai.orchestrator.orchestrator` y OpenRouter real con `max_tokens` controlado.
- `handle_message` de Telegram ya no responde echo; usa `telegram_ai_bridge -> orchestrator -> context_builder -> OpenRouter`.
- Telegram persiste mensajes `user` y `hermes` en `telegram_conversations` con fallback seguro si DB falla.
- `context_builder` agrega prioridades y riesgos operacionales derivados de PostgreSQL y runtime local.
- `orchestrator` incluye `priorities`, `risks` y `runtime` en el contexto enviado al provider.
- Runner sigue offline por decision operativa; no se habilito en esta fase.
- Cloud sigue fuera de alcance; no se desplego ni se parcheo cloud.

## FUNCIONA

- FastAPI importa correctamente.
- OpenAPI responde.
- PostgreSQL conecta desde local.
- `/health` responde 200.
- `/status` responde 200 con DB conectada.
- `/ready` responde 200 con DB conectada.
- `/runtime/status` responde 200.
- CRUD tasks responde y persiste en PostgreSQL.
- Telegram tiene token y chat id configurados localmente.
- Telegram handlers basicos registrados: `/start`, `/status`, `/tasks`, `/task`, `/pending`.
- `app.integrations.claude_client` existe y carga.
- 3.6.1 bloquea requests reales por defecto.
- 3.6.2 context isolation existe y sanitiza secretos.
- 3.6.3 context builder existe, consulta PostgreSQL y construye contexto operacional.
- `/ai/test` conecta 3.6.2 + 3.6.3 + `claude_client`, pero responde sin provider real.

## ROTO

- Cloud no fue validado ni limpiado en esta auditoria local.
- No se valido Telegram polling live para evitar doble polling si Render sigue activo.
- Runner no debe arrancar todavia segun decision CTO.
- Modulos IA avanzados existen, pero no deben considerarse operacionales todavia.

## FALTA

- Eliminar backend/workers/cron de Render desde dashboard.
- Ejecutar `deleteWebhook` solo despues de apagar Render.
- Validar Telegram solo local, sin respuestas duplicadas.
- Validar startup/shutdown con `uvicorn` local en una terminal controlada.
- Hacer commit limpio por bloque cuando el CTO lo autorice.
- Rehabilitar Runner en una fase posterior, limpio y validado.
- Validar provider real Anthropic/OpenRouter en fase posterior, con credenciales locales y flag explicito.

## IMPORTS ROTOS

- Core auditado sin imports rotos:
  - `app.main`
  - `app.api.ai`
  - `app.api.health`
  - `app.api.runtime`
  - `app.api.status`
  - `app.routers.tasks`
  - `app.telegram.client`
  - `app.telegram.handler`
  - `app.telegram.polling`
  - `app.integrations.claude_client`
  - `app.ai.context_isolation`
  - `app.ai.context_builder`
  - `app.ai.guardrails`
  - `app.repositories.task_repository`
  - `app.services.task_service`
  - `app.services.runtime_status`
  - `app.models.task`
  - `app.schemas.task`

## MODULOS FANTASMA

- `app.ai.orchestrator`: presente, avanzado, no conectado al startup ni a `/ai/test`.
- `app.ai.provider_registry`: presente, avanzado, no conectado al startup.
- `app.ai.providers.openrouter_provider`: presente, futuro, no conectado.
- `app.ai.telegram_bridge`: presente, futuro, no conectado a Telegram.
- `app.runner.task_runner`: presente, pero no arrancado en startup por decision CTO.
- Scripts `fix_*.py`: historico de reparaciones; no son runtime.

## ENDPOINTS OK

- `GET /health` -> 200.
- `GET /status` -> 200.
- `GET /ready` -> 200.
- `GET /runtime/status` -> 200.
- `GET /openapi.json` -> 200.
- `POST /ai/test` -> 200, `provider_not_configured` controlado.
- `POST /tasks` -> 201.
- `GET /tasks` -> 200.
- `GET /tasks/{task_id}` -> 200/404 segun exista.
- `PATCH /tasks/{task_id}` -> 200.
- `PATCH /tasks/{task_id}/status` -> 200.
- `PATCH /tasks/{task_id}/retry` -> registrado; requiere task `failed`.
- `DELETE /tasks/{task_id}` -> 204/404 segun exista.

## ENDPOINTS ROTOS

- Ninguno detectado en validacion ASGI local.
- Pendiente validacion con servidor `uvicorn` real y lifecycle completo.

## TELEGRAM STATUS

- `TELEGRAM_BOT_TOKEN`: configurado.
- `TELEGRAM_CHAT_ID`: configurado.
- Handlers registrados localmente: `/start`, `/status`, `/tasks`, `/task`, `/pending`.
- `/ask`: no registrado por freeze CTO.
- Polling live no validado en esta pasada para evitar conflicto si cloud sigue activo.
- Riesgo real: doble polling si Render sigue ejecutando backend Hermes.

## DB STATUS

- PostgreSQL conecta desde local.
- CRUD tasks validado contra DB real.
- `POST /tasks` devuelve estado inicial `pending` sin carrera con runner.
- Context builder consulta DB real y construye contexto.
- Riesgo: DB remota introduce latencias de varios segundos en context builder.

## 3.6.2 - CONTEXT ISOLATION

- Conectado a `/ai/test` via `_build_ai_test_prompt`.
- Redacta `sk-ant-*`, bearer tokens, `DATABASE_URL`, password y URLs PostgreSQL.
- Trunca texto largo.
- Aisla metadata a valores simples.
- Incluye `_isolation` con conteo de chars y bandera `truncated`.

## 3.6.3 - OPERATIONAL CONTEXT BUILDER

- Conectado a `/ai/test`.
- Usa `TaskRepository` y `runtime_status`.
- No usa SQL raw.
- No accede a filesystem.
- No lee env vars ni secretos.
- Produce summary, tasks, incidents, runtime y metadata.
- Riesgo: hace varias consultas por status; aceptable para auditoria, optimizable despues.

## VALIDACIONES EJECUTADAS

- `python -m py_compile ...` -> OK.
- Import audit core -> OK, 18 modulos.
- `pytest -q tests\test_ai_phase_3_6_1.py` -> 5 passed.
- `pytest -q tests\test_hermes.py` -> 12 passed.
- Endpoint smoke ASGI -> OK:
  - `/health`
  - `/status`
  - `/ready`
  - `/runtime/status`
  - `/openapi.json`
  - `/ai/test`

## DECISION OPERACIONAL

- Local base estable para fase auditada.
- 3.6.2 y 3.6.3 quedan conectadas de forma segura.
- Provider real sigue bloqueado.
- Runner sigue fuera de startup.
- Siguiente paso recomendado: limpiar cloud/Render y validar Telegram solo local antes de continuar.
