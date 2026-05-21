"""
Read-only task discovery for the runtime loop.

This layer only finds valid candidates for future pickup. It never claims,
locks, executes, retries, or mutates tasks.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, cast, func, select

from app.core.config import settings
from app.db.engine import AsyncSessionLocal
from app.models.task import Task
from app.schemas.task import TaskStatus

logger = logging.getLogger(__name__)

TASK_DISCOVERY_ALLOWED_STATUS = TaskStatus.pending.value
TASK_DISCOVERY_FILTERS = {"status": TASK_DISCOVERY_ALLOWED_STATUS}
TASK_DISCOVERY_ORDERING = (
    "status=pending",
    "created_at ASC",
    "retry_count ASC",
    "id ASC",
)

RowProvider = Callable[[int], Awaitable[Sequence[Mapping[str, Any]]]]


@dataclass(frozen=True)
class TaskDiscoveryCandidate:
    id: str
    title: str
    status: str
    phase: str | None
    retry_count: int
    max_retries: int
    created_at: str
    payload_size_bytes: int
    eligibility: str = "ready"
    runtime_scope: str = "current_database"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "phase": self.phase,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "payload_size_bytes": self.payload_size_bytes,
            "eligibility": self.eligibility,
            "runtime_scope": self.runtime_scope,
        }


@dataclass(frozen=True)
class TaskDiscoveryResult:
    status: str
    discovered_count: int
    candidates: tuple[TaskDiscoveryCandidate, ...] = field(default_factory=tuple)
    ignored_count: int = 0
    ignored_reasons: dict[str, int] = field(default_factory=dict)
    duration_ms: int = 0
    limit: int = 0
    max_payload_bytes: int = 0
    query_timeout_seconds: float = 0.0
    filters: dict[str, str] = field(default_factory=lambda: dict(TASK_DISCOVERY_FILTERS))
    ordering: tuple[str, ...] = TASK_DISCOVERY_ORDERING

    @classmethod
    def from_count(cls, count: int, duration_ms: int = 0) -> "TaskDiscoveryResult":
        safe_count = max(0, int(count or 0))
        return cls(
            status="tasks_discovered" if safe_count else "empty",
            discovered_count=safe_count,
            duration_ms=max(0, int(duration_ms or 0)),
            limit=safe_count,
            max_payload_bytes=0,
            query_timeout_seconds=0.0,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "discovered_count": self.discovered_count,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "ignored_count": self.ignored_count,
            "ignored_reasons": dict(self.ignored_reasons),
            "duration_ms": self.duration_ms,
            "limit": self.limit,
            "max_payload_bytes": self.max_payload_bytes,
            "query_timeout_seconds": self.query_timeout_seconds,
            "filters": dict(self.filters),
            "ordering": list(self.ordering),
        }


def _row_value(row: Mapping[str, Any], key: str) -> Any:
    return row[key] if key in row else None


def _row_has(row: Mapping[str, Any], key: str) -> bool:
    return key in row


def _payload_size_bytes(payload: dict[str, Any] | None) -> int:
    if payload is None:
        return 0
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    return len(encoded.encode("utf-8"))


def _datetime_to_iso(value: Any) -> str | None:
    if not isinstance(value, datetime):
        return None
    return value.isoformat()


def _sort_created_at(value: Any) -> datetime:
    if not isinstance(value, datetime):
        return datetime.max.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def validate_task_candidate(
    row: Mapping[str, Any],
    max_payload_bytes: int,
) -> tuple[TaskDiscoveryCandidate | None, str | None]:
    status = _row_value(row, "status")
    if status != TASK_DISCOVERY_ALLOWED_STATUS:
        return None, "invalid_status"

    task_id = _row_value(row, "id")
    if not task_id:
        return None, "missing_id"

    title = _row_value(row, "title")
    if not isinstance(title, str) or not title.strip():
        return None, "invalid_title"

    created_at = _datetime_to_iso(_row_value(row, "created_at"))
    if created_at is None:
        return None, "missing_created_at"

    payload_size = 0
    if _row_has(row, "payload_size_bytes"):
        payload_type = _row_value(row, "payload_type")
        if payload_type not in (None, "object", "null"):
            return None, "invalid_payload"
        payload_size = _safe_int(_row_value(row, "payload_size_bytes"), default=0)
    else:
        payload = _row_value(row, "payload")
        if payload is not None and not isinstance(payload, dict):
            return None, "invalid_payload"
        try:
            payload_size = _payload_size_bytes(payload)
        except (TypeError, ValueError):
            return None, "invalid_payload"

    if payload_size > max_payload_bytes:
        return None, "payload_too_large"

    retry_count = _safe_int(_row_value(row, "retry_count"), default=0)
    max_retries = _safe_int(_row_value(row, "max_retries"), default=3)
    if retry_count < 0 or max_retries < 0:
        return None, "invalid_retry_state"
    if retry_count > max_retries:
        return None, "retry_limit_exceeded"

    return (
        TaskDiscoveryCandidate(
            id=str(task_id),
            title=title,
            status=status,
            phase=_row_value(row, "phase"),
            retry_count=retry_count,
            max_retries=max_retries,
            created_at=created_at,
            payload_size_bytes=payload_size,
        ),
        None,
    )


class TaskDiscovery:
    def __init__(
        self,
        limit: int = settings.TASK_DISCOVERY_LIMIT,
        max_payload_bytes: int = settings.TASK_DISCOVERY_MAX_PAYLOAD_BYTES,
        query_timeout_seconds: float = settings.TASK_DISCOVERY_QUERY_TIMEOUT_SECONDS,
        row_provider: RowProvider | None = None,
    ) -> None:
        self.limit = max(1, int(limit or 1))
        self.max_payload_bytes = max(1, int(max_payload_bytes or 1))
        self.query_timeout_seconds = max(0.1, float(query_timeout_seconds or 0.1))
        self.row_provider = row_provider

    async def discover(self, limit: int | None = None) -> TaskDiscoveryResult:
        started = time.perf_counter()
        safe_limit = self._safe_limit(limit)
        try:
            rows = await asyncio.wait_for(
                self._fetch_rows(safe_limit),
                timeout=self.query_timeout_seconds,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.error(
                "task_discovery: error duration_ms=%s limit=%s error=%s",
                duration_ms,
                safe_limit,
                exc,
            )
            raise
        ordered_rows = self._ordered_rows(rows)[:safe_limit]

        candidates: list[TaskDiscoveryCandidate] = []
        ignored_reasons: dict[str, int] = {}
        seen_ids: set[str] = set()

        for row in ordered_rows:
            candidate, reason = validate_task_candidate(
                row=row,
                max_payload_bytes=self.max_payload_bytes,
            )
            if reason is not None:
                ignored_reasons[reason] = ignored_reasons.get(reason, 0) + 1
                continue
            assert candidate is not None
            if candidate.id in seen_ids:
                ignored_reasons["duplicate_id"] = (
                    ignored_reasons.get("duplicate_id", 0) + 1
                )
                continue
            seen_ids.add(candidate.id)
            candidates.append(candidate)

        duration_ms = int((time.perf_counter() - started) * 1000)
        result = TaskDiscoveryResult(
            status="tasks_discovered" if candidates else "empty",
            discovered_count=len(candidates),
            candidates=tuple(candidates),
            ignored_count=sum(ignored_reasons.values()),
            ignored_reasons=ignored_reasons,
            duration_ms=duration_ms,
            limit=safe_limit,
            max_payload_bytes=self.max_payload_bytes,
            query_timeout_seconds=self.query_timeout_seconds,
        )
        self._log_result(result)
        return result

    async def _fetch_rows(self, limit: int) -> Sequence[Mapping[str, Any]]:
        if self.row_provider is not None:
            return await self.row_provider(limit)

        statement = (
            select(
                Task.id.label("id"),
                Task.title.label("title"),
                Task.status.label("status"),
                Task.phase.label("phase"),
                func.json_typeof(Task.payload).label("payload_type"),
                func.coalesce(
                    func.length(cast(Task.payload, String)),
                    0,
                ).label("payload_size_bytes"),
                Task.retry_count.label("retry_count"),
                Task.max_retries.label("max_retries"),
                Task.created_at.label("created_at"),
            )
            .where(Task.status == TASK_DISCOVERY_ALLOWED_STATUS)
            .order_by(Task.created_at.asc(), Task.retry_count.asc(), Task.id.asc())
            .limit(limit)
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(statement)
            return result.mappings().all()

    def _safe_limit(self, limit: int | None) -> int:
        if limit is None:
            return self.limit
        return max(1, min(int(limit), self.limit))

    def _ordered_rows(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> list[Mapping[str, Any]]:
        return sorted(
            rows,
            key=lambda row: (
                _sort_created_at(_row_value(row, "created_at")),
                _safe_int(_row_value(row, "retry_count"), default=0),
                str(_row_value(row, "id") or ""),
            ),
        )

    def _log_result(self, result: TaskDiscoveryResult) -> None:
        if result.discovered_count or result.ignored_count:
            logger.info(
                "task_discovery: completed status=%s discovered=%s ignored=%s "
                "duration_ms=%s limit=%s filters=%s",
                result.status,
                result.discovered_count,
                result.ignored_count,
                result.duration_ms,
                result.limit,
                result.filters,
            )
            return
        logger.debug(
            "task_discovery: empty duration_ms=%s limit=%s filters=%s",
            result.duration_ms,
            result.limit,
            result.filters,
        )
