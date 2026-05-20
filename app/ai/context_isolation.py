"""
Context isolation for AI prompts.
Only sanitized operational summaries may leave Hermes.
"""
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 8000
MAX_TEXT_CHARS = MAX_CONTEXT_CHARS

_REDACT_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9\-_]{10,}"), "sk-ant-****"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-_.~+/]+=*", re.IGNORECASE), "Bearer ****"),
    (re.compile(r"postgresql\+asyncpg://[^\s]+", re.IGNORECASE), "postgresql+asyncpg://****"),
    (re.compile(r"DATABASE_URL\s*=\s*\S+", re.IGNORECASE), "DATABASE_URL=****"),
    (re.compile(r"password\s*=\s*\S+", re.IGNORECASE), "password=****"),
]


def redact_secrets(text: str) -> tuple[str, int]:
    redactions = 0
    for pattern, replacement in _REDACT_PATTERNS:
        text, count = pattern.subn(replacement, text)
        redactions += count
    return text, redactions


def truncate_safe(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + "... [TRUNCATED]", True


def sanitize_text(value: Any, max_chars: int = MAX_TEXT_CHARS) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    text, redactions = redact_secrets(text)
    text, truncated = truncate_safe(text, max_chars=max_chars)
    if truncated:
        logger.info("context_isolation: text truncated max_chars=%s", max_chars)
    if redactions:
        logger.info("context_isolation: redactions=%s", redactions)
    return text


def build_task_context(tasks: list[dict]) -> list[dict]:
    safe_tasks = []
    for task in tasks:
        safe_tasks.append(
            {
                "id": str(task.get("id", "")),
                "title": sanitize_text(task.get("title", "")),
                "description": sanitize_text(task.get("description", "")),
                "status": str(task.get("status", "")),
                "phase": sanitize_text(task.get("phase", "")),
                "error": sanitize_text(task.get("error", "")) if task.get("error") else None,
                "retry_count": int(task.get("retry_count", 0)),
            }
        )
    return safe_tasks


def build_operational_context(
    tasks: list[dict] | None = None,
    incidents: list[str] | None = None,
    priorities: list[str] | None = None,
    summary: str | None = None,
    runtime: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    safe_metadata = {}
    for key, value in (metadata or {}).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe_metadata[str(key)] = value

    context = {
        "tasks": build_task_context(tasks or []),
        "incidents": [sanitize_text(item) for item in (incidents or [])],
        "priorities": [sanitize_text(item) for item in (priorities or [])],
        "summary": sanitize_text(summary or ""),
        "runtime": runtime or {},
        "metadata": safe_metadata,
    }
    total_chars = safe_json_chars(context)
    context["_isolation"] = {
        "total_chars": total_chars,
        "truncated": total_chars > MAX_CONTEXT_CHARS,
        "redactions": 0,
    }
    logger.info(
        "context_isolation: context_built total_chars=%s truncated=%s tasks=%s",
        total_chars,
        context["_isolation"]["truncated"],
        len(context["tasks"]),
    )
    return context


def safe_json_chars(value: dict) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str))
