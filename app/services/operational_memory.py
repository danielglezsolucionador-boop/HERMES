"""
Simple operational memory backed by telegram_conversations.
No embeddings, vector DB, RAG, agents, or autonomous workflows.
"""
from __future__ import annotations

import logging
import re
import unicodedata

from app.ai.context_isolation import sanitize_text
from app.db.engine import AsyncSessionLocal
from app.repositories.conversation_repository import get_recent
from app.services.operational_summary import (
    build_operational_response,
    classify_operational_query,
    load_operational_snapshot,
)

logger = logging.getLogger(__name__)

MEMORY_LIMIT = 12
MAX_MEMORY_CHARS = 1600

FOLLOW_UP_TERMS = [
    "eso",
    "lo anterior",
    "lo ultimo",
    "ya se resolvio",
    "se resolvio",
    "quedo resuelto",
    "sigue igual",
    "que paso despues",
    "paso despues",
    "despues",
    "y ahora",
    "y eso",
]

DECISION_TERMS = [
    "decision",
    "decidimos",
    "decidido",
    "queda decidido",
    "vamos a",
    "se mantiene",
    "aprobado",
    "prioridad es",
]


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", without_accents.lower()).strip()


def is_memory_followup(query: str) -> bool:
    text = _normalize(query)
    return any(term in text for term in FOLLOW_UP_TERMS)


async def maybe_handle_memory_query(query: str) -> str | None:
    if not is_memory_followup(query):
        return None

    memory = await load_operational_memory(current_query=query)
    route = memory.get("last_route")
    if not route:
        return "\n".join(
            [
                "No tengo contexto operacional reciente suficiente para resolver ese seguimiento.",
                "Puedo responder si preguntas por tareas fallidas, atrasos, riesgos, runtime o que paso hoy.",
            ]
        )

    snapshot = await load_operational_snapshot()
    resolution = _resolution_line(route, snapshot)
    detail = await build_operational_response(route)
    last_user = memory.get("last_user_message") or "-"

    return "\n".join(
        [
            "Memoria operacional reciente",
            f"Contexto: la ultima consulta operacional fue: \"{last_user}\"",
            resolution,
            "",
            "Estado actual del mismo tema:",
            detail,
        ]
    )


async def build_memory_augmented_prompt(query: str) -> str:
    memory = await load_operational_memory(current_query=query)
    if not memory.get("recent_messages"):
        return query

    lines = [
        "CONTEXTO CONVERSACIONAL RECIENTE",
        "Fuente: PostgreSQL telegram_conversations.",
        "Usa este contexto solo si es relevante. No inventes memoria ni datos ausentes.",
    ]
    if memory.get("last_route"):
        lines.append(f"Ultimo tema operacional: {memory['last_route']}")
    if memory.get("recent_priorities"):
        lines.append("Prioridades recientes:")
        lines.extend(f"- {item}" for item in memory["recent_priorities"])
    if memory.get("recent_decisions"):
        lines.append("Decisiones recientes explicitas:")
        lines.extend(f"- {item}" for item in memory["recent_decisions"])
    if memory.get("recent_task_refs"):
        lines.append("Tasks recientes mencionadas:")
        lines.extend(f"- {item}" for item in memory["recent_task_refs"])

    lines.append("Mensajes recientes:")
    for item in memory["recent_messages"]:
        message = sanitize_text(item["message"], max_chars=220)
        lines.append(f"- {item['role']}: {message}")

    lines.extend(["", "USER REQUEST", query])
    prompt = "\n".join(lines)
    return prompt[:MAX_MEMORY_CHARS]


async def load_operational_memory(current_query: str | None = None) -> dict:
    rows = await _get_recent_conversation(MEMORY_LIMIT)
    rows = _drop_current_query(rows, current_query)

    last_user_message = None
    last_route = None
    for row in reversed(rows):
        if row["role"] == "user":
            if last_user_message is None:
                last_user_message = row["message"]
            route = classify_operational_query(row["message"])
            if route:
                last_route = route
                break

    if last_route is None:
        for row in reversed(rows):
            if row["role"] == "hermes":
                last_route = _route_from_hermes_message(row["message"])
                if last_route:
                    break

    priorities = _extract_recent_priorities(rows)
    decisions = _extract_recent_decisions(rows)
    task_refs = _extract_recent_task_refs(rows)

    return {
        "recent_messages": rows,
        "last_user_message": last_user_message,
        "last_route": last_route,
        "recent_priorities": priorities,
        "recent_decisions": decisions,
        "recent_task_refs": task_refs,
    }


async def _get_recent_conversation(limit: int) -> list[dict]:
    async with AsyncSessionLocal() as session:
        return await get_recent(session, limit=limit)


def _drop_current_query(rows: list[dict], current_query: str | None) -> list[dict]:
    if not rows or not current_query:
        return rows
    normalized_query = _normalize(current_query)
    clean_rows = list(rows)
    while clean_rows:
        last = clean_rows[-1]
        if last["role"] == "user" and _normalize(last["message"]) == normalized_query:
            clean_rows.pop()
            continue
        break
    return clean_rows


def _route_from_hermes_message(message: str) -> str | None:
    text = _normalize(message)
    if "tasks fallidas" in text:
        return "failed"
    if "atraso operacional" in text:
        return "delayed"
    if "riesgos operacionales" in text:
        return "risks"
    if "runtime operacional" in text:
        return "runtime"
    if "resumen operacional" in text:
        return "summary"
    return None


def _extract_recent_priorities(rows: list[dict]) -> list[str]:
    priorities = []
    capture = False
    for row in rows:
        if row["role"] != "hermes":
            continue
        for raw_line in row["message"].splitlines():
            line = raw_line.strip()
            lowered = _normalize(line)
            if lowered in {"prioridades:", "prioridad:"}:
                capture = True
                continue
            if capture and line.startswith("- "):
                priorities.append(line[2:])
                continue
            if capture and line and not line.startswith("- "):
                capture = False
    return _unique_tail(priorities, limit=5)


def _extract_recent_decisions(rows: list[dict]) -> list[str]:
    decisions = []
    for row in rows:
        for raw_line in row["message"].splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lowered = _normalize(line)
            if any(term in lowered for term in DECISION_TERMS):
                decisions.append(sanitize_text(line, max_chars=180))
    return _unique_tail(decisions, limit=5)


def _extract_recent_task_refs(rows: list[dict]) -> list[str]:
    refs = []
    pattern = re.compile(r"^-\s+([0-9a-f]{8})\s+(.+?)\s+\[[a-z_]+\]", re.I)
    for row in rows:
        if row["role"] != "hermes":
            continue
        for line in row["message"].splitlines():
            match = pattern.match(line.strip())
            if match:
                refs.append(f"{match.group(1)} {match.group(2)}")
    return _unique_tail(refs, limit=5)


def _unique_tail(items: list[str], limit: int) -> list[str]:
    seen = set()
    result = []
    for item in reversed(items):
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= limit:
            break
    return list(reversed(result))


def _resolution_line(route: str, snapshot: dict) -> str:
    counts = snapshot["counts"]
    runner = snapshot["runner"]
    if route == "failed":
        failed = counts.get("failed", 0)
        if failed:
            return f"No esta resuelto: quedan {failed} task(s) failed en PostgreSQL."
        return "Si: no quedan tasks failed en PostgreSQL."
    if route == "delayed":
        doing = counts.get("doing", 0)
        pending = counts.get("pending", 0)
        runner_status = runner.get("runner_status", "unknown")
        if runner_status == "offline" and doing:
            return f"No esta resuelto: runner offline con {doing} task(s) en doing."
        if pending:
            return f"Parcial: no hay bloqueo doing/offline, pero quedan {pending} pending."
        return "Si: no hay senal operacional de atraso con los datos actuales."
    if route == "risks":
        failed = counts.get("failed", 0)
        doing = counts.get("doing", 0)
        runner_status = runner.get("runner_status", "unknown")
        if failed or (runner_status == "offline" and doing):
            return "No esta resuelto: siguen existiendo riesgos operacionales reales."
        return "Si: no hay riesgos criticos detectados con los datos actuales."
    if route == "runtime":
        status = runner.get("runner_status", "unknown")
        if status == "healthy":
            return "Si: runtime reporta healthy."
        return f"No esta resuelto: runtime reporta {status}."
    return "Estado actualizado desde PostgreSQL y runtime local."
