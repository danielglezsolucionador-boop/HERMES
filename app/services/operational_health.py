"""
Operational health engine for local Hermes runtime.
All checks are derived from real local runtime, PostgreSQL, providers, and Telegram.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider_registry import provider_registry, setup_registry
from app.services.operational_risks import build_operational_risks
from app.services.runtime_status import runtime_status
from app.telegram.client import validate_connection

DB_DEGRADED_MS = 2000
DB_UNHEALTHY_MS = 5000
AI_DEGRADED_MS = 15000
AI_UNHEALTHY_MS = 25000
TELEGRAM_DEGRADED_MS = 5000


async def build_operational_health(
    session: AsyncSession,
    task_counts: dict,
) -> dict:
    runtime = runtime_status.to_dict()
    checks = {
        "database": await _check_database(session),
        "ai": await _check_ai_provider(runtime),
        "telegram": await _check_telegram(runtime),
        "runtime": _check_runtime(runtime),
        "tasks": _check_tasks(task_counts),
    }
    status = _overall_status(checks)
    health = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "reasons": _reasons(checks),
    }
    health["risks"] = build_operational_risks(health, task_counts, runtime)
    return health


async def _check_database(session: AsyncSession) -> dict:
    start = time.monotonic()
    try:
        await session.execute(text("SELECT 1"))
        latency_ms = int((time.monotonic() - start) * 1000)
        status = "healthy"
        if latency_ms >= DB_UNHEALTHY_MS:
            status = "unhealthy"
        elif latency_ms >= DB_DEGRADED_MS:
            status = "degraded"
        return {
            "status": status,
            "connected": True,
            "latency_ms": latency_ms,
            "last_error": None,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "status": "unhealthy",
            "connected": False,
            "latency_ms": latency_ms,
            "last_error": str(exc),
        }


async def _check_ai_provider(runtime: dict) -> dict:
    start = time.monotonic()
    try:
        if provider_registry.active_name() is None:
            setup_registry()
        provider = provider_registry.get_active()
        provider_health = await provider.healthcheck()
        latency_ms = int((time.monotonic() - start) * 1000)
        configured = bool(provider_health.get("configured"))
        avg_ms = runtime.get("ai_avg_duration_ms", 0)
        failed = runtime.get("ai_requests_failed", 0)
        status = "healthy"
        if not configured:
            status = "unhealthy"
        elif avg_ms >= AI_UNHEALTHY_MS:
            status = "unhealthy"
        elif avg_ms >= AI_DEGRADED_MS or failed:
            status = "degraded"
        return {
            "status": status,
            "provider": provider.provider_name,
            "configured": configured,
            "available": bool(provider_health.get("available")),
            "latency_ms": latency_ms,
            "last_model": runtime.get("last_model") or runtime.get("last_ai_model"),
            "last_request_at": runtime.get("last_ai_request_at"),
            "last_error": runtime.get("last_ai_error") or provider_health.get("last_error"),
            "avg_duration_ms": avg_ms,
            "requests_total": runtime.get("ai_requests_total", 0),
            "requests_failed": failed,
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "status": "unhealthy",
            "provider": provider_registry.active_name(),
            "configured": False,
            "available": False,
            "latency_ms": latency_ms,
            "last_error": str(exc),
        }


async def _check_telegram(runtime: dict) -> dict:
    start = time.monotonic()
    try:
        connected = await asyncio.wait_for(validate_connection(), timeout=8)
        latency_ms = int((time.monotonic() - start) * 1000)
        failed = runtime.get("telegram_messages_failed", 0)
        status = "healthy"
        if not connected:
            status = "unhealthy"
        elif latency_ms >= TELEGRAM_DEGRADED_MS or failed:
            status = "degraded"
        return {
            "status": status,
            "connected": connected,
            "latency_ms": latency_ms,
            "messages_total": runtime.get("telegram_messages_total", 0),
            "messages_failed": failed,
            "last_message_at": runtime.get("telegram_last_message_at"),
            "last_error": runtime.get("telegram_last_error"),
        }
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return {
            "status": "unhealthy",
            "connected": False,
            "latency_ms": latency_ms,
            "messages_total": runtime.get("telegram_messages_total", 0),
            "messages_failed": runtime.get("telegram_messages_failed", 0),
            "last_message_at": runtime.get("telegram_last_message_at"),
            "last_error": str(exc),
        }


def _check_runtime(runtime: dict) -> dict:
    runner_status = runtime.get("runner_status", "unknown")
    avg_ms = runtime.get("ai_avg_duration_ms", 0)
    status = "healthy"
    if runner_status == "offline":
        status = "degraded"
    if avg_ms >= AI_UNHEALTHY_MS:
        status = "unhealthy"
    elif avg_ms >= AI_DEGRADED_MS:
        status = "degraded"
    return {
        "status": status,
        "runner_status": runner_status,
        "runner_alive": runtime.get("runner_alive"),
        "last_loop_at": runtime.get("last_loop_at"),
        "ai_avg_duration_ms": avg_ms,
    }


def _check_tasks(task_counts: dict) -> dict:
    failed = task_counts.get("failed", 0)
    pending = task_counts.get("pending", 0)
    doing = task_counts.get("doing", 0)
    status = "healthy"
    if failed >= 10:
        status = "unhealthy"
    elif failed or pending >= 20 or doing >= 20:
        status = "degraded"
    return {
        "status": status,
        "total": sum(task_counts.values()),
        "failed": failed,
        "pending": pending,
        "doing": doing,
        "review": task_counts.get("review", 0),
        "done": task_counts.get("done", 0),
    }


def _overall_status(checks: dict) -> str:
    statuses = [value.get("status") for value in checks.values()]
    if "unhealthy" in statuses:
        return "unhealthy"
    if "degraded" in statuses:
        return "degraded"
    return "healthy"


def _reasons(checks: dict) -> list[str]:
    reasons = []
    for name, check in checks.items():
        if check.get("status") == "healthy":
            continue
        detail = check.get("last_error") or check.get("runner_status") or check.get("status")
        reasons.append(f"{name}: {detail}")
    return reasons
