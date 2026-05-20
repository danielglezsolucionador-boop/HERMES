"""
Operational risk derivation from real runtime, health, and task data.
"""
from __future__ import annotations


def build_operational_risks(
    health: dict,
    task_counts: dict,
    runtime: dict,
) -> list[dict]:
    risks: list[dict] = []
    checks = health.get("checks", {})

    db = checks.get("database", {})
    if db.get("status") != "healthy":
        risks.append(
            _risk(
                "critical",
                "database",
                "database connectivity degraded",
                db,
            )
        )
    elif db.get("latency_ms", 0) >= 2000:
        risks.append(
            _risk(
                "medium",
                "database",
                "database latency high",
                {"latency_ms": db.get("latency_ms")},
            )
        )

    ai = checks.get("ai", {})
    if ai.get("status") != "healthy":
        risks.append(_risk("high", "ai", "AI provider degraded", ai))
    elif runtime.get("ai_requests_failed", 0) > 0:
        risks.append(
            _risk(
                "medium",
                "ai",
                "AI requests have recent failures",
                {
                    "ai_requests_failed": runtime.get("ai_requests_failed", 0),
                    "last_ai_error": runtime.get("last_ai_error"),
                },
            )
        )
    elif runtime.get("ai_avg_duration_ms", 0) >= 15000:
        risks.append(
            _risk(
                "medium",
                "ai",
                "AI runtime latency high",
                {"ai_avg_duration_ms": runtime.get("ai_avg_duration_ms")},
            )
        )

    telegram = checks.get("telegram", {})
    if telegram.get("status") != "healthy":
        risks.append(_risk("high", "telegram", "Telegram degraded", telegram))
    elif runtime.get("telegram_messages_failed", 0) > 0:
        risks.append(
            _risk(
                "medium",
                "telegram",
                "Telegram message delivery failures detected",
                {
                    "telegram_messages_failed": runtime.get("telegram_messages_failed", 0),
                    "telegram_last_error": runtime.get("telegram_last_error"),
                },
            )
        )

    failed = task_counts.get("failed", 0)
    if failed >= 10:
        risks.append(
            _risk("high", "tasks", "high failed tasks", {"failed_tasks": failed})
        )
    elif failed > 0:
        risks.append(
            _risk("medium", "tasks", "failed tasks present", {"failed_tasks": failed})
        )

    doing = task_counts.get("doing", 0)
    runner_status = runtime.get("runner_status")
    if doing > 0 and runner_status == "offline":
        risks.append(
            _risk(
                "high",
                "runtime",
                "runtime unstable: runner offline with doing tasks",
                {"doing": doing, "runner_status": runner_status},
            )
        )

    pending = task_counts.get("pending", 0)
    if pending >= 20:
        risks.append(
            _risk("medium", "tasks", "task backlog high", {"pending": pending})
        )

    return risks


def _risk(severity: str, source: str, message: str, evidence: dict) -> dict:
    return {
        "severity": severity,
        "source": source,
        "message": message,
        "evidence": evidence,
    }
