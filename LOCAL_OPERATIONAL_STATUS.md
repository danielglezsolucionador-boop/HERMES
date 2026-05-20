# HERMES LOCAL OPERATIONAL STATUS

## Recovery Status
- Recovery target: 3.8
- Status: PARTIAL
- Validation date: 2026-05-20 11:30 America/Lima
- Commit hash: 1262637b472f99f47fa43e6cc52b374310b110dc

## Components Working
- FastAPI application starts locally with `uvicorn app.main:app --reload`.
- FastAPI lifespan startup reaches application startup complete.
- FastAPI lifespan shutdown path cancels pending Telegram startup task cleanly and calls `stop_polling()`.
- PostgreSQL connectivity is working through SQLAlchemy async engine.
- CRUD tasks API works for create, list, and delete.
- `/health` responds with service status `ok`.
- `/status` responds with database status `connected`.
- `/runtime/status` returns live task counts, runner state, AI metrics, Telegram metrics, operational health, and operational risks.
- `/ai/test` responds through real OpenRouter.
- OpenRouter provider is configured and returns a successful AI response.
- Telegram bot API connection is valid.
- Telegram outbound delivery to the configured chat works.
- Operational Telegram response generation works for the required local operational queries.
- Operational health engine returns real component checks.
- Operational risks engine returns real risks from runtime and task data.
- Test suite passes.

## Components Not Yet Implemented
- No cross-process or external ownership lock exists to guarantee a single Telegram `getUpdates` consumer for the bot token.
- No `due_at` or equivalent due-date field exists for true overdue task detection; delayed summaries use runner/task status signals.
- The local runner is not active during API-only runtime, so runner heartbeat metrics remain offline unless the runner is started separately.
- Tests use the local PostgreSQL task table directly and leave operational-looking task records behind.

## Operational Risks
- Telegram polling is not globally unique: Telegram returned `Conflict: terminated by other getUpdates request; make sure that only one bot instance is running`.
- Operational health is `unhealthy` because runtime runner is offline and tasks are unhealthy.
- Task backlog at validation time: total 131, failed 11, doing 31, pending 30, done 59, review 0.
- Operational risks returned by `/runtime/status`:
  - high tasks: high failed tasks, evidence `failed_tasks=11`.
  - high runtime: runner offline with doing tasks, evidence `doing=31`, `runner_status=offline`.
  - medium tasks: task backlog high, evidence `pending=30`.

## API Endpoints Validated
- `/health`: HTTP 200, `status=ok`, `service=hermes`, `version=0.1.0`.
- `/status`: HTTP 200, `status=ok`, `database=connected`, `env=development`.
- `/runtime/status`: HTTP 200, `status=online`, task counts and operational health returned.
- `/ai/test`: HTTP 200 via GET, `success=true`, provider `openrouter`, model `deepseek/deepseek-chat-v3`.

## Telegram Operational Status
- Bot API connection: valid.
- Polling startup: starts and logs `Telegram polling -> activo`.
- Polling uniqueness: not validated as healthy. Telegram reports another active `getUpdates` consumer for the same bot token.
- Server runtime Telegram counters during API validation: `telegram_messages_processed=0`, `telegram_messages_failed=0`.
- Real outbound Telegram delivery was validated for:
  - `como estamos?`: sent true.
  - `hay problemas?`: sent true.
  - `runtime estable?`: sent true.
  - `que paso hoy?`: sent true.
  - `que tareas fallaron?`: sent true.
  - `que esta atrasado?`: sent true.
- Limitation: Codex cannot originate human Telegram messages from the authorized user account; validation used local operational response generation plus real Telegram outbound delivery.

## AI Operational Status
- Provider: OpenRouter.
- Model: `deepseek/deepseek-chat-v3`.
- Result: success true.
- Final `/ai/test` duration: 9664 ms.
- Provider duration: 5939 ms.
- Context build duration: 3709 ms.
- Error: null.

## Database Operational Status
- PostgreSQL status from `/status`: connected.
- Operational health database check: healthy.
- Database latency in final `/runtime/status`: 203 ms.
- CRUD validation:
  - create: HTTP 201, task id `48a415bd-31ec-4590-be6d-eeb300268a27`.
  - list: HTTP 200, returned 5 tasks with `limit=5`.
  - delete: HTTP 204 for created validation task.

## Runtime Observability
- `/runtime/status` exposes task counts, runner metrics, AI metrics, Telegram metrics, operational health, and operational risks.
- Final task counts: total 131, done 59, failed 11, doing 31, review 0, pending 30, running_legacy 0.
- Runner status: offline.
- Runner alive: false.
- AI metrics: total 1, success 1, failed 0, avg duration 9664 ms.
- Telegram metrics: total 0, failed 0, processed 0 in the server process.
- Operational health status: unhealthy.
- Operational risks count: 3.

## Test Suite Status
- Command: `pytest -q`.
- Result: 28 passed.
- Warnings: 2.
- Warnings observed:
  - Unknown pytest config option `asyncio_default_fixture_loop_scope`.
  - Deprecated custom `event_loop` fixture override from pytest-asyncio.

## Known Limitations
- Recovery 3.8 is not complete while another Telegram polling consumer is active for the same bot token.
- Operational health is intentionally reporting `unhealthy`; this reflects real task/runtime state, not a health engine failure.
- Local task runner metrics are offline during API-only validation.
- Existing failed, doing, and pending tasks require cleanup or diagnosis before declaring operationally clean state.
- Current tests are not isolated from the local operational PostgreSQL task data.

## Recommended Next Phase
- Do not advance to FASE 4 until Telegram polling ownership is resolved and only one `getUpdates` consumer remains active.
- Before FASE 4, reconcile failed/doing/pending tasks and decide whether the local runner must be started as part of the local operational profile.
- Add a local test database or cleanup fixture so validation tests do not pollute operational task counts.
