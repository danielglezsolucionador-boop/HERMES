"""
Operational summaries for Telegram.
Uses PostgreSQL tasks and in-memory runtime status as source of truth.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, or_, select

from app.db.engine import AsyncSessionLocal
from app.models.task import Task
from app.schemas.task import TaskStatus
from app.services.operational_health import build_operational_health
from app.services.runtime_status import runtime_status

logger = logging.getLogger(__name__)

try:
    LOCAL_TZ = ZoneInfo("America/Lima")
except ZoneInfoNotFoundError:
    LOCAL_TZ = timezone(timedelta(hours=-5))
MAX_TASK_LINES = 5


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def classify_operational_query(query: str) -> str | None:
    text = _normalize(query)
    if not text:
        return None

    if any(term in text for term in ["ai timeout", "ia timeout", "timeout ia", "timeout ai", "provider timeout"]):
        return "ai_timeout"
    if any(term in text for term in ["retries", "retry", "reintento", "reintentos"]):
        return "retries"
    if any(term in text for term in ["ultima task", "ultimas task", "ultimas tareas", "last tasks", "latest tasks"]):
        return "last_tasks"
    if any(term in text for term in ["backlog", "cola", "pendientes", "en cola"]):
        return "backlog"
    if any(term in text for term in ["riesgo", "riesgos"]):
        return "risks"
    if "telegram" in text and "estable" in text:
        return "telegram_health"
    if any(term in text for term in ["ia estable", "ai estable", "ai provider"]):
        return "ai_health"
    if "runtime" in text and "estable" in text:
        return "runtime_health"
    if any(term in text for term in ["como estamos", "como esta hermes"]):
        return "health"
    if any(term in text for term in ["hay problemas", "problemas", "que esta fallando", "esta fallando"]):
        return "issues"
    if any(term in text for term in ["fallaron", "fallidas", "fallida", "failed"]):
        return "failed"
    if any(
        term in text
        for term in ["atrasado", "atrasadas", "atrasada", "demorado", "bloqueado"]
    ):
        return "delayed"
    if any(term in text for term in ["runtime", "salud", "health"]):
        return "runtime"
    if any(
        term in text
        for term in [
            "que paso hoy",
            "paso hoy",
            "estado operacional",
            "estado operativo",
            "resumen operacional",
        ]
    ):
        return "summary"
    return None


async def maybe_handle_operational_query(query: str) -> str | None:
    route = classify_operational_query(query)
    if route is None:
        return None
    logger.info("operational_summary: routed query route=%s", route)
    return await build_operational_response(route)


async def build_operational_response(route: str) -> str:
    try:
        snapshot = await load_operational_snapshot()
    except Exception as exc:
        logger.error("operational_summary: DB unavailable error=%s", exc)
        return "\n".join(
            [
                "PostgreSQL no disponible para resumen operacional.",
                f"Runtime: {runtime_status.health_status()}",
                f"Detalle: {_clip(str(exc), 180)}",
            ]
        )

    if route == "failed":
        return _format_failed_summary(snapshot)
    if route == "backlog":
        return _format_backlog_summary(snapshot)
    if route == "retries":
        return _format_retry_summary(snapshot)
    if route == "ai_timeout":
        return _format_ai_timeout_summary(snapshot)
    if route == "last_tasks":
        return _format_last_tasks_summary(snapshot)
    if route in {"health", "issues", "ai_health", "telegram_health", "runtime_health"}:
        health = await _load_health(snapshot["counts"])
        if route == "issues":
            return _format_issue_summary(snapshot, health)
        if route == "ai_health":
            return _format_component_health("IA", "ai", health)
        if route == "telegram_health":
            return _format_component_health("Telegram", "telegram", health)
        if route == "runtime_health":
            return _format_component_health("Runtime", "runtime", health)
        return _format_health_summary(snapshot, health)
    if route == "delayed":
        return _format_delayed_summary(snapshot)
    if route == "risks":
        health = await _load_health(snapshot["counts"])
        return _format_risk_summary(snapshot, health)
    if route == "runtime":
        return _format_runtime_summary(snapshot)
    return _format_operational_summary(snapshot)


async def load_operational_snapshot() -> dict:
    return await _load_snapshot()


async def _load_health(counts: dict) -> dict:
    async with AsyncSessionLocal() as session:
        return await build_operational_health(session, counts)


async def _load_snapshot() -> dict:
    now_local = datetime.now(LOCAL_TZ)
    start_local = datetime.combine(now_local.date(), time.min, tzinfo=LOCAL_TZ)
    start_utc = start_local.astimezone(timezone.utc)

    counts = {status.value: 0 for status in TaskStatus}
    today_status_counts = {status.value: 0 for status in TaskStatus}

    async with AsyncSessionLocal() as session:
        count_rows = await session.execute(
            select(Task.status, func.count(Task.id)).group_by(Task.status)
        )
        for status, total in count_rows.all():
            counts[status] = total

        today_rows = await session.execute(
            select(Task.status, func.count(Task.id))
            .where(Task.updated_at >= start_utc)
            .group_by(Task.status)
        )
        for status, total in today_rows.all():
            today_status_counts[status] = total

        created_today = await session.scalar(
            select(func.count(Task.id)).where(Task.created_at >= start_utc)
        )
        completed_today = await session.scalar(
            select(func.count(Task.id)).where(Task.completed_at >= start_utc)
        )

        recent_today = await session.execute(
            select(Task)
            .where(
                or_(
                    Task.created_at >= start_utc,
                    Task.updated_at >= start_utc,
                    Task.completed_at >= start_utc,
                )
            )
            .order_by(Task.updated_at.desc())
            .limit(MAX_TASK_LINES)
        )
        failed_tasks = await session.execute(
            select(Task)
            .where(Task.status == TaskStatus.failed.value)
            .order_by(Task.updated_at.desc())
            .limit(MAX_TASK_LINES)
        )
        doing_tasks = await session.execute(
            select(Task)
            .where(Task.status == TaskStatus.doing.value)
            .order_by(Task.updated_at.asc())
            .limit(MAX_TASK_LINES)
        )
        pending_tasks = await session.execute(
            select(Task)
            .where(Task.status == TaskStatus.pending.value)
            .order_by(Task.created_at.asc())
            .limit(MAX_TASK_LINES)
        )
        recent_tasks = await session.execute(
            select(Task)
            .order_by(Task.updated_at.desc(), Task.created_at.desc())
            .limit(MAX_TASK_LINES)
        )

        recent_today_tasks = list(recent_today.scalars().all())
        failed = list(failed_tasks.scalars().all())
        doing = list(doing_tasks.scalars().all())
        pending = list(pending_tasks.scalars().all())
        recent = list(recent_tasks.scalars().all())

    runner = runtime_status.to_dict()
    priorities, risks = _build_priorities_and_risks(counts, runner)

    incidents = [
        f"{_task_ref(task)} - {_clip(task.error or 'failed sin error registrado', 120)}"
        for task in failed
    ]

    return {
        "generated_at": now_local,
        "counts": counts,
        "today_status_counts": today_status_counts,
        "created_today": int(created_today or 0),
        "completed_today": int(completed_today or 0),
        "recent_today_tasks": recent_today_tasks,
        "recent_tasks": recent,
        "failed_tasks": failed,
        "doing_tasks": doing,
        "pending_tasks": pending,
        "runner": runner,
        "priorities": priorities,
        "risks": risks,
        "incidents": incidents,
    }


def _build_priorities_and_risks(counts: dict, runner: dict) -> tuple[list[str], list[str]]:
    priorities = []
    risks = []
    runner_status = runner.get("runner_status", "unknown")

    if counts.get("failed", 0):
        priorities.append(f"Revisar {counts['failed']} task(s) fallidas.")
        risks.append(f"{counts['failed']} task(s) fallidas requieren diagnostico.")
    if counts.get("doing", 0) and runner_status == "offline":
        priorities.append(f"Auditar {counts['doing']} task(s) en doing con runner offline.")
        risks.append("Runner offline con tasks en doing puede indicar ejecucion detenida.")
    if counts.get("pending", 0):
        priorities.append(f"Procesar {counts['pending']} task(s) pendientes.")
    if runner.get("ai_failed_requests", 0):
        risks.append(f"{runner['ai_failed_requests']} request(s) AI fallaron en runtime local.")
    if not priorities:
        priorities.append("Mantener monitoreo; no hay pending ni failed.")
    if not risks:
        risks.append("Sin riesgos operacionales criticos detectados con los datos actuales.")
    return priorities, risks


def _format_operational_summary(snapshot: dict) -> str:
    counts = snapshot["counts"]
    today = snapshot["today_status_counts"]
    lines = [
        "Resumen operacional de hoy",
        (
            f"Tasks totales: {sum(counts.values())} | "
            f"pending {counts['pending']} | doing {counts['doing']} | "
            f"review {counts['review']} | done {counts['done']} | failed {counts['failed']}"
        ),
        (
            f"Hoy: creadas {snapshot['created_today']} | "
            f"completadas {snapshot['completed_today']} | "
            f"actualizadas failed {today['failed']} | doing {today['doing']}"
        ),
        _runtime_line(snapshot),
    ]
    lines.extend(_section("Prioridades", snapshot["priorities"]))
    lines.extend(_section("Incidentes reales", snapshot["incidents"]))
    lines.extend(_task_section("Movimientos recientes", snapshot["recent_today_tasks"]))
    return "\n".join(lines)


def _format_failed_summary(snapshot: dict) -> str:
    counts = snapshot["counts"]
    lines = [
        "Tasks fallidas",
        f"Total failed en PostgreSQL: {counts['failed']}",
        _runtime_line(snapshot),
    ]
    lines.extend(_task_section("Ultimas fallidas", snapshot["failed_tasks"], include_error=True))
    lines.extend(_section("Prioridad", snapshot["priorities"][:2]))
    return "\n".join(lines)


def _format_backlog_summary(snapshot: dict) -> str:
    counts = snapshot["counts"]
    backlog = counts["pending"] + counts["doing"]
    lines = [
        "Backlog operacional",
        f"Total backlog: {backlog} | pending {counts['pending']} | doing {counts['doing']}",
        _runtime_line(snapshot),
    ]
    lines.extend(_task_section("Pendientes mas antiguas", snapshot["pending_tasks"]))
    lines.extend(_task_section("En doing mas antiguas", snapshot["doing_tasks"]))
    return "\n".join(lines)


def _format_retry_summary(snapshot: dict) -> str:
    retry_tasks = [
        task
        for task in snapshot["failed_tasks"] + snapshot["pending_tasks"]
        if getattr(task, "retry_count", 0)
    ]
    lines = [
        "Reintentos operacionales",
        _runtime_line(snapshot),
    ]
    lines.extend(_retry_task_section("Tasks con reintentos registrados", retry_tasks))
    if not retry_tasks:
        lines.append("No veo reintentos registrados en las tasks recientes.")
    return "\n".join(lines)


def _format_ai_timeout_summary(snapshot: dict) -> str:
    runner = snapshot["runner"]
    timeout_tasks = [
        task
        for task in snapshot["failed_tasks"]
        if "timeout" in _normalize(getattr(task, "error", "") or "")
    ]
    lines = [
        "Timeout IA",
        (
            f"Requests IA: total {runner.get('total_ai_requests', 0)} | "
            f"fallidos {runner.get('ai_failed_requests', 0)} | "
            f"avg {runner.get('avg_ai_duration_ms', 0)}ms"
        ),
        (
            f"Ultimo provider: {runner.get('last_ai_provider') or '-'} | "
            f"ultimo error: {runner.get('last_ai_error') or '-'}"
        ),
    ]
    lines.extend(_task_section("Fallidas con timeout", timeout_tasks, include_error=True))
    return "\n".join(lines)


def _format_last_tasks_summary(snapshot: dict) -> str:
    recent_tasks = snapshot.get("recent_tasks") or snapshot["recent_today_tasks"]
    lines = [
        "Ultimas tasks",
        _runtime_line(snapshot),
    ]
    lines.extend(_task_section("Mas recientes", recent_tasks, include_error=True))
    return "\n".join(lines)


def _format_delayed_summary(snapshot: dict) -> str:
    counts = snapshot["counts"]
    runner_status = snapshot["runner"].get("runner_status", "unknown")
    lines = [
        "Atraso operacional",
        "No hay campo due_at; no invento vencimientos.",
        (
            f"Senal real usada: runner {runner_status}, "
            f"doing {counts['doing']}, pending {counts['pending']}."
        ),
    ]
    lines.extend(_task_section("En doing mas antiguas", snapshot["doing_tasks"]))
    lines.extend(_task_section("Pendientes mas antiguas", snapshot["pending_tasks"]))
    lines.extend(_section("Riesgos", snapshot["risks"]))
    return "\n".join(lines)


def _format_risk_summary(snapshot: dict, health: dict | None = None) -> str:
    lines = ["Riesgos operacionales", _runtime_line(snapshot)]
    if health:
        risk_lines = [
            f"{risk['severity']} {risk['source']}: {risk['message']}"
            for risk in health.get("risks", [])
        ]
        lines.extend(_section("Riesgos runtime", risk_lines))
    lines.extend(_section("Riesgos tasks", snapshot["risks"]))
    lines.extend(_section("Prioridades", snapshot["priorities"]))
    lines.extend(_section("Incidentes reales", snapshot["incidents"]))
    return "\n".join(lines)


def _format_health_summary(snapshot: dict, health: dict) -> str:
    checks = health.get("checks", {})
    lines = [
        "Salud operacional",
        f"Estado general: {health.get('status')}",
        _runtime_line(snapshot),
        (
            f"DB: {checks.get('database', {}).get('status')} "
            f"({checks.get('database', {}).get('latency_ms')}ms)"
        ),
        (
            f"IA: {checks.get('ai', {}).get('status')} | "
            f"provider {checks.get('ai', {}).get('provider') or '-'} | "
            f"modelo {checks.get('ai', {}).get('last_model') or '-'}"
        ),
        (
            f"Telegram: {checks.get('telegram', {}).get('status')} "
            f"({checks.get('telegram', {}).get('latency_ms')}ms)"
        ),
    ]
    risk_lines = [
        f"{risk['severity']} {risk['source']}: {risk['message']}"
        for risk in health.get("risks", [])
    ]
    lines.extend(_section("Riesgos", risk_lines))
    lines.extend(_section("Prioridades", snapshot["priorities"]))
    return "\n".join(lines)


def _format_issue_summary(snapshot: dict, health: dict) -> str:
    lines = [
        "Problemas operacionales",
        f"Estado general: {health.get('status')}",
    ]
    risk_lines = [
        f"{risk['severity']} {risk['source']}: {risk['message']}"
        for risk in health.get("risks", [])
    ]
    lines.extend(_section("Detectado", risk_lines))
    lines.extend(_section("Incidentes reales", snapshot["incidents"]))
    return "\n".join(lines)


def _format_component_health(label: str, key: str, health: dict) -> str:
    check = health.get("checks", {}).get(key, {})
    lines = [
        f"{label} estable",
        f"Estado: {check.get('status')}",
    ]
    for field in [
        "connected",
        "configured",
        "provider",
        "last_model",
        "last_request_at",
        "last_message_at",
        "avg_duration_ms",
        "latency_ms",
        "last_error",
        "runner_status",
    ]:
        if field in check:
            lines.append(f"{field}: {check.get(field)}")
    return "\n".join(lines)


def _format_runtime_summary(snapshot: dict) -> str:
    runner = snapshot["runner"]
    ai_total = runner.get("total_ai_requests", 0)
    ai_success = runner.get("ai_success_requests", 0)
    ai_failed = runner.get("ai_failed_requests", 0)
    return "\n".join(
        [
            "Runtime operacional",
            _runtime_line(snapshot),
            (
                f"AI: requests {ai_total} | success {ai_success} | failed {ai_failed} | "
                f"avg {runner.get('avg_ai_duration_ms', 0)}ms"
            ),
            (
                f"Ultimo provider: {runner.get('last_ai_provider') or '-'} | "
                f"modelo: {runner.get('last_ai_model') or '-'}"
            ),
            f"Telegram mensajes procesados: {runner.get('telegram_messages_processed', 0)}",
        ]
    )


def _runtime_line(snapshot: dict) -> str:
    runner = snapshot["runner"]
    return (
        f"Runtime: runner {runner.get('runner_status', 'unknown')} | "
        f"alive {runner.get('runner_alive')} | "
        f"loop {runner.get('last_loop_at') or '-'}"
    )


def _section(title: str, items: list[str]) -> list[str]:
    if not items:
        return [f"{title}: ninguno."]
    return [f"{title}:"] + [f"- {item}" for item in items[:MAX_TASK_LINES]]


def _task_section(title: str, tasks: list[Task], include_error: bool = False) -> list[str]:
    if not tasks:
        return [f"{title}: ninguna."]
    lines = [f"{title}:"]
    for task in tasks[:MAX_TASK_LINES]:
        line = f"- {_task_ref(task)} [{task.status}]"
        if include_error and task.error:
            line = f"{line} error={_clip(task.error, 100)}"
        lines.append(line)
    return lines


def _retry_task_section(title: str, tasks: list[Task]) -> list[str]:
    if not tasks:
        return [f"{title}: ninguna."]
    lines = [f"{title}:"]
    for task in tasks[:MAX_TASK_LINES]:
        retry_count = getattr(task, "retry_count", 0)
        max_retries = getattr(task, "max_retries", 0)
        last_retry = getattr(task, "last_retry_at", None)
        last_retry_text = last_retry.isoformat() if last_retry else "-"
        lines.append(
            f"- {_task_ref(task)} [{task.status}] retry {retry_count}/{max_retries} last={last_retry_text}"
        )
    return lines


def _task_ref(task: Task) -> str:
    title = _clip(task.title or "(sin titulo)", 80)
    return f"{str(task.id)[:8]} {title}"


def _clip(value: str, max_chars: int) -> str:
    clean = re.sub(r"\s+", " ", value or "").strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + "..."
