"""
Controlled operational memory for Hermes runtime.

This layer captures and retrieves operational records while preserving
traceability and governance safety. It keeps memory append-only inside the
runtime process and does not add persistence, bypass approvals, or mutate
execution state.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

MEMORY_TYPE_EXECUTION = "execution"
MEMORY_TYPE_GOVERNANCE = "governance"
MEMORY_TYPE_AUDIT = "audit"
MEMORY_TYPE_FAILURE = "failure"
MEMORY_TYPE_CONTINUATION = "continuation"
SUPPORTED_MEMORY_TYPES = {
    MEMORY_TYPE_EXECUTION,
    MEMORY_TYPE_GOVERNANCE,
    MEMORY_TYPE_AUDIT,
    MEMORY_TYPE_FAILURE,
    MEMORY_TYPE_CONTINUATION,
}

MEMORY_STATUS_CAPTURED = "captured"
MEMORY_STATUS_RETRIEVED = "retrieved"
MEMORY_STATUS_BLOCKED = "blocked"
MEMORY_STATUS_ERROR = "error"

BLOCKING_GOVERNANCE_STATUSES = {"blocked", "rejected", "critical", "escalated"}
BLOCKING_AUDIT_STATUSES = {"rejected", "needs_fix", "blocked"}


@dataclass(frozen=True)
class OperationalMemoryCaptureRequest:
    execution_id: str | None = None
    task_id: str | None = None
    memory_id: str | None = None
    memory_type: str = MEMORY_TYPE_EXECUTION
    workflow: str | None = None
    event_type: str | None = None
    memory_context: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    governance_status: str | None = None
    audit_status: str | None = None
    risk_level: str | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    governance_history: tuple[Any, ...] = field(default_factory=tuple)
    audit_history: tuple[Any, ...] = field(default_factory=tuple)
    workflow_history: tuple[Any, ...] = field(default_factory=tuple)
    continuation_history: tuple[Any, ...] = field(default_factory=tuple)
    existing_records: tuple[Any, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationalMemoryQuery:
    execution_id: str | None = None
    memory_type: str | None = None
    workflow: str | None = None
    query_context: dict[str, Any] = field(default_factory=dict)
    memory_records: tuple[Any, ...] = field(default_factory=tuple)
    allow_cross_execution: bool = False
    reuse_permitted: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationalMemoryResult:
    status: str
    success: bool
    memory_id: str | None
    execution_id: str | None
    task_id: str | None
    memory_type: str | None
    workflow: str | None
    event_type: str | None
    governance_status: str | None
    audit_status: str | None
    risk_level: str | None
    memory_context: dict[str, Any] = field(default_factory=dict)
    memory_record: dict[str, Any] = field(default_factory=dict)
    memory_records: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    reusable_context: dict[str, Any] = field(default_factory=dict)
    integrity_valid: bool = False
    context_safe: bool = False
    governance_safe: bool = False
    traceability_preserved: bool = False
    reuse_allowed: bool = False
    critical_memory_preserved: bool = False
    matched_records: int = 0
    corrupt_records: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    governance_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    audit_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    workflow_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    continuation_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    memory_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    timestamp: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "memory_id": self.memory_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "memory_type": self.memory_type,
            "workflow": self.workflow,
            "event_type": self.event_type,
            "governance_status": self.governance_status,
            "audit_status": self.audit_status,
            "risk_level": self.risk_level,
            "memory_context": dict(self.memory_context),
            "memory_record": dict(self.memory_record),
            "memory_records": [dict(record) for record in self.memory_records],
            "reusable_context": dict(self.reusable_context),
            "integrity_valid": self.integrity_valid,
            "context_safe": self.context_safe,
            "governance_safe": self.governance_safe,
            "traceability_preserved": self.traceability_preserved,
            "reuse_allowed": self.reuse_allowed,
            "critical_memory_preserved": self.critical_memory_preserved,
            "matched_records": self.matched_records,
            "corrupt_records": self.corrupt_records,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "governance_history": [
                dict(entry) for entry in self.governance_history
            ],
            "audit_history": [dict(entry) for entry in self.audit_history],
            "workflow_history": [
                dict(entry) for entry in self.workflow_history
            ],
            "continuation_history": [
                dict(entry) for entry in self.continuation_history
            ],
            "memory_lifecycle": [
                dict(entry) for entry in self.memory_lifecycle
            ],
            "timestamp": self.timestamp,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class OperationalMemory:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status
        self.records: list[dict[str, Any]] = []

    def capture(
        self,
        request: OperationalMemoryCaptureRequest,
        memory_permitted: bool = True,
    ) -> OperationalMemoryResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        memory_id = request.memory_id or str(uuid4())

        try:
            memory_type = self._memory_type(request.memory_type)
            reasons = self._capture_reasons(
                request=request,
                memory_id=memory_id,
                memory_type=memory_type,
                memory_permitted=memory_permitted,
            )
            if reasons:
                result = self._capture_result(
                    status=MEMORY_STATUS_BLOCKED,
                    success=False,
                    memory_id=memory_id,
                    request=request,
                    memory_type=memory_type,
                    memory_record={},
                    integrity_valid=False,
                    context_safe="context_incompatible" not in reasons,
                    governance_safe="governance_bypass_detected" not in reasons,
                    reuse_allowed=False,
                    lifecycle=(
                        self._lifecycle("memory_capture_requested"),
                        self._lifecycle(MEMORY_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            record = self._memory_record(memory_id, memory_type, request)
            self.records.append(record)
            result = self._capture_result(
                status=MEMORY_STATUS_CAPTURED,
                success=True,
                memory_id=memory_id,
                request=request,
                memory_type=memory_type,
                memory_record=record,
                integrity_valid=True,
                context_safe=True,
                governance_safe=True,
                reuse_allowed=False,
                lifecycle=(
                    self._lifecycle("memory_capture_requested"),
                    self._lifecycle("memory_stored_append_only"),
                    self._lifecycle(MEMORY_STATUS_CAPTURED),
                ),
                reasons=["memory_preserved_append_only"],
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                memory_id=memory_id,
                execution_id=request.execution_id,
                memory_type=request.memory_type,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def retrieve(
        self,
        query: OperationalMemoryQuery,
    ) -> OperationalMemoryResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)

        try:
            memory_type = self._memory_type(query.memory_type)
            records = [
                *[dict(record) for record in self.records],
                *[self._as_dict(record) for record in query.memory_records],
            ]
            matches, corrupt = self._matching_records(query, records, memory_type)
            governance_safe = self._retrieval_governance_safe(query, matches)
            reasons = self._retrieval_reasons(
                query=query,
                corrupt=corrupt,
                governance_safe=governance_safe,
            )
            if reasons:
                result = self._retrieve_result(
                    status=MEMORY_STATUS_BLOCKED,
                    success=False,
                    query=query,
                    memory_type=memory_type,
                    matches=matches,
                    corrupt=corrupt,
                    governance_safe=governance_safe,
                    reuse_allowed=False,
                    reusable_context={},
                    lifecycle=(
                        self._lifecycle("memory_retrieval_requested"),
                        self._lifecycle(MEMORY_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            reusable_context = self._reusable_context(matches)
            result = self._retrieve_result(
                status=MEMORY_STATUS_RETRIEVED,
                success=True,
                query=query,
                memory_type=memory_type,
                matches=matches,
                corrupt=corrupt,
                governance_safe=governance_safe,
                reuse_allowed=bool(matches),
                reusable_context=reusable_context,
                lifecycle=(
                    self._lifecycle("memory_retrieval_requested"),
                    self._lifecycle("memory_consistency_validated"),
                    self._lifecycle(MEMORY_STATUS_RETRIEVED),
                ),
                reasons=[] if matches else ["no_memory_matches"],
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                memory_id=None,
                execution_id=query.execution_id,
                memory_type=query.memory_type,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _capture_result(
        self,
        status: str,
        success: bool,
        memory_id: str | None,
        request: OperationalMemoryCaptureRequest,
        memory_type: str | None,
        memory_record: dict[str, Any],
        integrity_valid: bool,
        context_safe: bool,
        governance_safe: bool,
        reuse_allowed: bool,
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> OperationalMemoryResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        timestamp = memory_record.get("timestamp") or finished_at.isoformat()
        return OperationalMemoryResult(
            status=status,
            success=success,
            memory_id=memory_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            memory_type=memory_type,
            workflow=request.workflow,
            event_type=request.event_type,
            governance_status=self._normalize(request.governance_status),
            audit_status=self._normalize(request.audit_status),
            risk_level=self._normalize(request.risk_level),
            memory_context=dict(request.memory_context or {}),
            memory_record=memory_record,
            memory_records=tuple([memory_record] if memory_record else []),
            reusable_context={},
            integrity_valid=integrity_valid,
            context_safe=context_safe,
            governance_safe=governance_safe,
            traceability_preserved=True,
            reuse_allowed=reuse_allowed,
            critical_memory_preserved=self._critical_memory(request),
            matched_records=1 if memory_record else 0,
            corrupt_records=0,
            errors=tuple(request.errors),
            warnings=tuple(request.warnings),
            governance_history=tuple(
                self._as_dict(entry) for entry in request.governance_history
            ),
            audit_history=tuple(
                self._as_dict(entry) for entry in request.audit_history
            ),
            workflow_history=tuple(
                self._as_dict(entry) for entry in request.workflow_history
            ),
            continuation_history=tuple(
                self._as_dict(entry) for entry in request.continuation_history
            ),
            memory_lifecycle=lifecycle,
            timestamp=timestamp,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _retrieve_result(
        self,
        status: str,
        success: bool,
        query: OperationalMemoryQuery,
        memory_type: str | None,
        matches: list[dict[str, Any]],
        corrupt: list[dict[str, Any]],
        governance_safe: bool,
        reuse_allowed: bool,
        reusable_context: dict[str, Any],
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> OperationalMemoryResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        first = matches[0] if matches else {}
        return OperationalMemoryResult(
            status=status,
            success=success,
            memory_id=first.get("memory_id"),
            execution_id=query.execution_id,
            task_id=first.get("task_id"),
            memory_type=memory_type,
            workflow=query.workflow or first.get("workflow"),
            event_type=first.get("event_type"),
            governance_status=first.get("governance_status"),
            audit_status=first.get("audit_status"),
            risk_level=first.get("risk_level"),
            memory_context=dict(first.get("memory_context") or {}),
            memory_record=first,
            memory_records=tuple(matches),
            reusable_context=reusable_context,
            integrity_valid=not corrupt,
            context_safe=True,
            governance_safe=governance_safe,
            traceability_preserved=True,
            reuse_allowed=reuse_allowed,
            critical_memory_preserved=any(
                self._record_is_critical(record) for record in matches
            ),
            matched_records=len(matches),
            corrupt_records=len(corrupt),
            errors=tuple(
                str(error)
                for record in matches
                for error in (record.get("errors") or [])
            ),
            warnings=tuple(
                str(warning)
                for record in matches
                for warning in (record.get("warnings") or [])
            ),
            governance_history=tuple(
                entry
                for record in matches
                for entry in self._history(record, "governance_history")
            ),
            audit_history=tuple(
                entry
                for record in matches
                for entry in self._history(record, "audit_history")
            ),
            workflow_history=tuple(
                entry
                for record in matches
                for entry in self._history(record, "workflow_history")
            ),
            continuation_history=tuple(
                entry
                for record in matches
                for entry in self._history(record, "continuation_history")
            ),
            memory_lifecycle=lifecycle,
            timestamp=first.get("timestamp"),
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(query.metadata),
        )

    def _capture_reasons(
        self,
        request: OperationalMemoryCaptureRequest,
        memory_id: str,
        memory_type: str | None,
        memory_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not memory_permitted:
            reasons.append("operational_memory_not_permitted")
        if memory_type not in SUPPORTED_MEMORY_TYPES:
            reasons.append("unsupported_memory_type")
        if not request.execution_id:
            reasons.append("missing_execution_id")
        if not self._has_payload(request):
            reasons.append("missing_memory_context")
        if not self._context_safe(request):
            reasons.append("context_incompatible")
        if self._memory_id_exists(memory_id, request.existing_records):
            reasons.append("memory_overwrite_detected")
        if self._governance_bypass_detected(request.memory_context):
            reasons.append("governance_bypass_detected")
        return self._unique(reasons)

    def _retrieval_reasons(
        self,
        query: OperationalMemoryQuery,
        corrupt: list[dict[str, Any]],
        governance_safe: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not query.reuse_permitted:
            reasons.append("memory_reuse_not_permitted")
        if corrupt:
            reasons.append("memory_corruption_detected")
        if not governance_safe:
            reasons.append("governance_memory_blocks_reuse")
        if self._governance_bypass_detected(query.query_context):
            reasons.append("governance_bypass_detected")
        return self._unique(reasons)

    def _memory_record(
        self,
        memory_id: str,
        memory_type: str,
        request: OperationalMemoryCaptureRequest,
    ) -> dict[str, Any]:
        return {
            "memory_id": memory_id,
            "execution_id": request.execution_id,
            "task_id": request.task_id,
            "memory_type": memory_type,
            "workflow": request.workflow,
            "event_type": request.event_type,
            "memory_context": dict(request.memory_context),
            "outputs": dict(request.outputs),
            "governance_status": self._normalize(request.governance_status),
            "audit_status": self._normalize(request.audit_status),
            "risk_level": self._normalize(request.risk_level),
            "errors": list(request.errors),
            "warnings": list(request.warnings),
            "governance_history": [
                self._as_dict(entry) for entry in request.governance_history
            ],
            "audit_history": [
                self._as_dict(entry) for entry in request.audit_history
            ],
            "workflow_history": [
                self._as_dict(entry) for entry in request.workflow_history
            ],
            "continuation_history": [
                self._as_dict(entry) for entry in request.continuation_history
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": dict(request.metadata),
        }

    def _matching_records(
        self,
        query: OperationalMemoryQuery,
        records: list[dict[str, Any]],
        memory_type: str | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        matches: list[dict[str, Any]] = []
        corrupt: list[dict[str, Any]] = []
        seen: set[str] = set()
        for record in records:
            if not record:
                continue
            if not self._record_valid(record):
                corrupt.append(record)
                continue
            memory_id = str(record.get("memory_id"))
            if memory_id in seen:
                continue
            seen.add(memory_id)
            if memory_type and record.get("memory_type") != memory_type:
                continue
            if query.execution_id and not query.allow_cross_execution:
                if record.get("execution_id") != query.execution_id:
                    continue
            if query.workflow and record.get("workflow") != query.workflow:
                continue
            matches.append(record)
        return matches, corrupt

    def _retrieval_governance_safe(
        self,
        query: OperationalMemoryQuery,
        matches: list[dict[str, Any]],
    ) -> bool:
        if not query.query_context.get("use_for_continuation"):
            return True
        for record in matches:
            governance_status = self._normalize(record.get("governance_status"))
            audit_status = self._normalize(record.get("audit_status"))
            if governance_status in BLOCKING_GOVERNANCE_STATUSES:
                return False
            if audit_status in BLOCKING_AUDIT_STATUSES:
                return False
        return True

    def _reusable_context(self, matches: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "records": [
                {
                    "memory_id": record.get("memory_id"),
                    "memory_type": record.get("memory_type"),
                    "workflow": record.get("workflow"),
                    "event_type": record.get("event_type"),
                    "memory_context": dict(record.get("memory_context") or {}),
                    "outputs": dict(record.get("outputs") or {}),
                    "timestamp": record.get("timestamp"),
                }
                for record in matches
            ]
        }

    def _record_valid(self, record: dict[str, Any]) -> bool:
        return bool(
            record.get("memory_id")
            and record.get("execution_id")
            and record.get("memory_type") in SUPPORTED_MEMORY_TYPES
            and record.get("timestamp")
            and isinstance(record.get("memory_context"), dict)
        )

    def _has_payload(self, request: OperationalMemoryCaptureRequest) -> bool:
        return any(
            (
                request.memory_context,
                request.outputs,
                request.errors,
                request.warnings,
                request.governance_history,
                request.audit_history,
                request.workflow_history,
                request.continuation_history,
            )
        )

    def _context_safe(self, request: OperationalMemoryCaptureRequest) -> bool:
        context_execution_id = request.memory_context.get("execution_id")
        if context_execution_id and context_execution_id != request.execution_id:
            return False
        return True

    def _memory_id_exists(self, memory_id: str, records: tuple[Any, ...]) -> bool:
        for record in [*self.records, *[self._as_dict(item) for item in records]]:
            if record.get("memory_id") == memory_id:
                return True
        return False

    def _governance_bypass_detected(self, value: dict[str, Any]) -> bool:
        text = " ".join(str(item).lower() for item in value.values())
        return "skip approval" in text or "bypass governance" in text

    def _critical_memory(self, request: OperationalMemoryCaptureRequest) -> bool:
        return bool(
            request.errors
            or request.warnings
            or request.memory_type in {MEMORY_TYPE_GOVERNANCE, MEMORY_TYPE_AUDIT}
            or self._normalize(request.risk_level) in {"critical", "severe"}
        )

    def _record_is_critical(self, record: dict[str, Any]) -> bool:
        return bool(
            record.get("errors")
            or record.get("warnings")
            or record.get("memory_type") in {MEMORY_TYPE_GOVERNANCE, MEMORY_TYPE_AUDIT}
            or record.get("risk_level") in {"critical", "severe"}
        )

    def _history(self, record: dict[str, Any], key: str) -> list[dict[str, Any]]:
        return [
            self._as_dict(entry)
            for entry in (record.get(key) or [])
            if isinstance(self._as_dict(entry), dict)
        ]

    def _memory_type(self, value: str | None) -> str | None:
        return self._normalize(value)

    def _normalize(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {"value": str(value)}
        return {"value": str(value)}

    def _lifecycle(self, state: str) -> dict[str, Any]:
        return {
            "state": state,
            "at": datetime.now(timezone.utc).isoformat(),
        }

    def _unique(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                unique.append(value)
        return unique

    def _error_result(
        self,
        memory_id: str | None,
        execution_id: str | None,
        memory_type: str | None,
        error: str,
        started: float,
        started_at: datetime,
    ) -> OperationalMemoryResult:
        finished_at = datetime.now(timezone.utc)
        return OperationalMemoryResult(
            status=MEMORY_STATUS_ERROR,
            success=False,
            memory_id=memory_id,
            execution_id=execution_id,
            task_id=None,
            memory_type=self._memory_type(memory_type),
            workflow=None,
            event_type=None,
            governance_status=None,
            audit_status=None,
            risk_level=None,
            integrity_valid=False,
            context_safe=False,
            governance_safe=False,
            traceability_preserved=True,
            reuse_allowed=False,
            critical_memory_preserved=False,
            memory_lifecycle=(self._lifecycle(MEMORY_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("operational_memory_error_contained",),
            error=error,
        )

    def _publish(self, result: OperationalMemoryResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_operational_memory_result",
        ):
            self.status.mark_operational_memory_result(result.to_dict())

    def _log_result(self, result: OperationalMemoryResult) -> None:
        if result.status == MEMORY_STATUS_ERROR:
            logger.error(
                "operational_memory: error memory_id=%s error=%s",
                result.memory_id,
                result.error,
            )
            return
        if result.status == MEMORY_STATUS_BLOCKED:
            logger.warning(
                "operational_memory: blocked memory_id=%s reasons=%s",
                result.memory_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "operational_memory: %s memory_id=%s execution_id=%s type=%s",
            result.status,
            result.memory_id,
            result.execution_id,
            result.memory_type,
        )
