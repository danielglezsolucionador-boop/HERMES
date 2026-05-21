"""
Controlled workflow learning for Hermes runtime.

This layer analyzes operational memory and extracts visible learning signals.
It never changes governance, runtime rules, architecture, or execution behavior
automatically; optimizations remain suggestions until external governance
permits reuse.
"""
from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.operational_memory import OperationalMemoryResult

logger = logging.getLogger(__name__)

LEARNING_TYPE_SUCCESS = "success_pattern"
LEARNING_TYPE_FAILURE = "failure_pattern"
LEARNING_TYPE_AUDIT = "audit"
LEARNING_TYPE_CONTINUATION = "continuation"
LEARNING_TYPE_EXECUTION = "execution"
SUPPORTED_LEARNING_TYPES = {
    LEARNING_TYPE_SUCCESS,
    LEARNING_TYPE_FAILURE,
    LEARNING_TYPE_AUDIT,
    LEARNING_TYPE_CONTINUATION,
    LEARNING_TYPE_EXECUTION,
}

LEARNING_STATUS_LEARNED = "learned"
LEARNING_STATUS_NO_PATTERNS = "no_patterns"
LEARNING_STATUS_BLOCKED = "blocked"
LEARNING_STATUS_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
    "governance_approved",
}
APPROVED_AUDIT_STATUSES = {"approved", "approved_with_warnings"}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable"}


@dataclass(frozen=True)
class WorkflowLearningRequest:
    execution_id: str | None = None
    task_id: str | None = None
    workflow: str | None = None
    learning_type: str = LEARNING_TYPE_EXECUTION
    memory_records: tuple[Any, ...] = field(default_factory=tuple)
    execution_history: tuple[Any, ...] = field(default_factory=tuple)
    governance_history: tuple[Any, ...] = field(default_factory=tuple)
    audit_history: tuple[Any, ...] = field(default_factory=tuple)
    continuation_history: tuple[Any, ...] = field(default_factory=tuple)
    governance_status: str | None = None
    audit_status: str | None = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    reuse_requested: bool = False
    governance_override_requested: bool = False
    allow_critical_rule_change: bool = False
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowLearningResult:
    status: str
    success: bool
    learning_id: str
    execution_id: str | None
    task_id: str | None
    workflow: str | None
    learning_type: str | None
    pattern_type: str | None
    learning_status: str
    governance_status: str | None
    audit_status: str | None
    optimization_status: str
    governance_compliant: bool
    audit_consistent: bool
    runtime_safe: bool
    context_safe: bool
    traceability_preserved: bool
    reuse_allowed: bool
    autonomy_expanded: bool
    memory_analyzed: bool
    learning_validated: bool
    patterns_detected: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    execution_insights: tuple[str, ...] = field(default_factory=tuple)
    workflow_improvements: tuple[str, ...] = field(default_factory=tuple)
    recurrent_errors: tuple[str, ...] = field(default_factory=tuple)
    audit_expectations: tuple[str, ...] = field(default_factory=tuple)
    memory_records: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    execution_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    governance_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    audit_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    continuation_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    learning_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "learning_id": self.learning_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "workflow": self.workflow,
            "learning_type": self.learning_type,
            "pattern_type": self.pattern_type,
            "learning_status": self.learning_status,
            "governance_status": self.governance_status,
            "audit_status": self.audit_status,
            "optimization_status": self.optimization_status,
            "governance_compliant": self.governance_compliant,
            "audit_consistent": self.audit_consistent,
            "runtime_safe": self.runtime_safe,
            "context_safe": self.context_safe,
            "traceability_preserved": self.traceability_preserved,
            "reuse_allowed": self.reuse_allowed,
            "autonomy_expanded": self.autonomy_expanded,
            "memory_analyzed": self.memory_analyzed,
            "learning_validated": self.learning_validated,
            "patterns_detected": [
                dict(pattern) for pattern in self.patterns_detected
            ],
            "execution_insights": list(self.execution_insights),
            "workflow_improvements": list(self.workflow_improvements),
            "recurrent_errors": list(self.recurrent_errors),
            "audit_expectations": list(self.audit_expectations),
            "memory_records": [dict(record) for record in self.memory_records],
            "execution_history": [
                dict(entry) for entry in self.execution_history
            ],
            "governance_history": [
                dict(entry) for entry in self.governance_history
            ],
            "audit_history": [dict(entry) for entry in self.audit_history],
            "continuation_history": [
                dict(entry) for entry in self.continuation_history
            ],
            "learning_lifecycle": [
                dict(entry) for entry in self.learning_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class WorkflowLearning:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def analyze(
        self,
        request: WorkflowLearningRequest,
        learning_permitted: bool = True,
        runtime_active: bool = True,
    ) -> WorkflowLearningResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        learning_id = str(uuid4())

        try:
            learning_type = self._learning_type(request.learning_type)
            records = [self._as_dict(record) for record in request.memory_records]
            corrupt = [record for record in records if not self._record_valid(record)]
            governance_status = self._governance_status(request, records)
            audit_status = self._audit_status(request, records)
            checks = {
                "governance_compliant": self._governance_compliant(
                    request,
                    governance_status,
                ),
                "audit_consistent": self._audit_consistent(request, audit_status),
                "runtime_safe": runtime_active and self._runtime_safe(request),
                "context_safe": not corrupt,
            }
            reasons = self._validation_reasons(
                request=request,
                learning_type=learning_type,
                checks=checks,
                corrupt=corrupt,
                learning_permitted=learning_permitted,
            )
            if reasons:
                result = self._result(
                    status=LEARNING_STATUS_BLOCKED,
                    success=False,
                    learning_id=learning_id,
                    request=request,
                    learning_type=learning_type,
                    pattern_type=None,
                    learning_status=LEARNING_STATUS_BLOCKED,
                    governance_status=governance_status,
                    audit_status=audit_status,
                    optimization_status="blocked",
                    checks=checks,
                    reuse_allowed=False,
                    memory_analyzed=bool(records),
                    learning_validated=False,
                    patterns=[],
                    insights=[],
                    improvements=[],
                    recurrent_errors=[],
                    audit_expectations=[],
                    records=records,
                    lifecycle=(
                        self._lifecycle("memory_analysis_requested"),
                        self._lifecycle(LEARNING_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            patterns = self._detect_patterns(learning_type, records)
            insights = self._execution_insights(patterns)
            improvements = self._workflow_improvements(patterns)
            recurrent_errors = tuple(
                pattern["signal"]
                for pattern in patterns
                if pattern.get("pattern_type") == LEARNING_TYPE_FAILURE
            )
            audit_expectations = tuple(
                pattern["signal"]
                for pattern in patterns
                if pattern.get("pattern_type") == LEARNING_TYPE_AUDIT
            )
            learned = bool(patterns)
            result = self._result(
                status=(
                    LEARNING_STATUS_LEARNED
                    if learned
                    else LEARNING_STATUS_NO_PATTERNS
                ),
                success=True,
                learning_id=learning_id,
                request=request,
                learning_type=learning_type,
                pattern_type=learning_type,
                learning_status=(
                    "learning_validated"
                    if learned
                    else LEARNING_STATUS_NO_PATTERNS
                ),
                governance_status=governance_status,
                audit_status=audit_status,
                optimization_status=(
                    "suggested_only" if learned else "not_available"
                ),
                checks=checks,
                reuse_allowed=bool(learned and request.reuse_requested),
                memory_analyzed=True,
                learning_validated=learned,
                patterns=patterns,
                insights=insights,
                improvements=improvements,
                recurrent_errors=list(recurrent_errors),
                audit_expectations=list(audit_expectations),
                records=records,
                lifecycle=(
                    self._lifecycle("memory_analysis_requested"),
                    self._lifecycle("pattern_detection_completed"),
                    self._lifecycle("learning_validated"),
                ),
                reasons=(
                    []
                    if not learned or request.reuse_requested
                    else ["learning_reuse_requires_governance"]
                ),
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                learning_id=learning_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _result(
        self,
        status: str,
        success: bool,
        learning_id: str,
        request: WorkflowLearningRequest,
        learning_type: str | None,
        pattern_type: str | None,
        learning_status: str,
        governance_status: str | None,
        audit_status: str | None,
        optimization_status: str,
        checks: dict[str, bool],
        reuse_allowed: bool,
        memory_analyzed: bool,
        learning_validated: bool,
        patterns: list[dict[str, Any]],
        insights: list[str],
        improvements: list[str],
        recurrent_errors: list[str],
        audit_expectations: list[str],
        records: list[dict[str, Any]],
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> WorkflowLearningResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return WorkflowLearningResult(
            status=status,
            success=success,
            learning_id=learning_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            workflow=request.workflow,
            learning_type=learning_type,
            pattern_type=pattern_type,
            learning_status=learning_status,
            governance_status=governance_status,
            audit_status=audit_status,
            optimization_status=optimization_status,
            governance_compliant=checks["governance_compliant"],
            audit_consistent=checks["audit_consistent"],
            runtime_safe=checks["runtime_safe"],
            context_safe=checks["context_safe"],
            traceability_preserved=True,
            reuse_allowed=reuse_allowed,
            autonomy_expanded=False,
            memory_analyzed=memory_analyzed,
            learning_validated=learning_validated,
            patterns_detected=tuple(patterns),
            execution_insights=tuple(insights),
            workflow_improvements=tuple(improvements),
            recurrent_errors=tuple(recurrent_errors),
            audit_expectations=tuple(audit_expectations),
            memory_records=tuple(records),
            execution_history=tuple(
                self._as_dict(entry) for entry in request.execution_history
            ),
            governance_history=tuple(
                self._as_dict(entry) for entry in request.governance_history
            ),
            audit_history=tuple(
                self._as_dict(entry) for entry in request.audit_history
            ),
            continuation_history=tuple(
                self._as_dict(entry) for entry in request.continuation_history
            ),
            learning_lifecycle=lifecycle,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _detect_patterns(
        self,
        learning_type: str | None,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if learning_type == LEARNING_TYPE_SUCCESS:
            return self._success_patterns(records)
        if learning_type == LEARNING_TYPE_FAILURE:
            return self._failure_patterns(records)
        if learning_type == LEARNING_TYPE_AUDIT:
            return self._audit_patterns(records)
        if learning_type == LEARNING_TYPE_CONTINUATION:
            return self._continuation_patterns(records)
        return self._execution_patterns(records)

    def _success_patterns(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        patterns: list[dict[str, Any]] = []
        workflows = Counter(
            record.get("workflow")
            for record in records
            if record.get("workflow")
            and not record.get("errors")
            and self._normalize(record.get("governance_status"))
            in APPROVED_GOVERNANCE_STATUSES
            and self._normalize(record.get("audit_status")) in APPROVED_AUDIT_STATUSES
        )
        for workflow, count in workflows.items():
            patterns.append(
                self._pattern(LEARNING_TYPE_SUCCESS, str(workflow), count, records)
            )
        return patterns

    def _failure_patterns(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        errors = Counter(
            str(error)
            for record in records
            for error in (record.get("errors") or [])
            if error
        )
        return [
            self._pattern(LEARNING_TYPE_FAILURE, signal, count, records)
            for signal, count in errors.items()
            if count >= 2
        ]

    def _audit_patterns(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        signals = Counter(
            str(signal)
            for record in records
            for signal in [
                *(record.get("warnings") or []),
                record.get("audit_status"),
            ]
            if signal and self._normalize(signal) != "approved"
        )
        return [
            self._pattern(LEARNING_TYPE_AUDIT, signal, count, records)
            for signal, count in signals.items()
        ]

    def _continuation_patterns(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        signals = Counter(
            record.get("workflow")
            for record in records
            if record.get("memory_type") == "continuation" and record.get("workflow")
        )
        return [
            self._pattern(LEARNING_TYPE_CONTINUATION, str(signal), count, records)
            for signal, count in signals.items()
        ]

    def _execution_patterns(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        signals = Counter(
            record.get("event_type")
            for record in records
            if record.get("event_type") and record.get("memory_type") == "execution"
        )
        return [
            self._pattern(LEARNING_TYPE_EXECUTION, str(signal), count, records)
            for signal, count in signals.items()
        ]

    def _pattern(
        self,
        pattern_type: str,
        signal: str,
        count: int,
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "pattern_id": str(uuid4()),
            "pattern_type": pattern_type,
            "signal": signal,
            "count": count,
            "evidence_memory_ids": [
                record.get("memory_id")
                for record in records
                if self._record_mentions(record, signal)
            ],
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    def _record_mentions(self, record: dict[str, Any], signal: str) -> bool:
        values = [
            record.get("workflow"),
            record.get("event_type"),
            record.get("audit_status"),
            *(record.get("errors") or []),
            *(record.get("warnings") or []),
        ]
        return signal in {str(value) for value in values if value}

    def _execution_insights(self, patterns: list[dict[str, Any]]) -> list[str]:
        return [
            f"{pattern['pattern_type']}:{pattern['signal']} count={pattern['count']}"
            for pattern in patterns
        ]

    def _workflow_improvements(self, patterns: list[dict[str, Any]]) -> list[str]:
        improvements: list[str] = []
        for pattern in patterns:
            if pattern["pattern_type"] == LEARNING_TYPE_SUCCESS:
                improvements.append(
                    f"reuse validated workflow context for {pattern['signal']}"
                )
            elif pattern["pattern_type"] == LEARNING_TYPE_FAILURE:
                improvements.append(
                    f"add preflight check for recurrent error {pattern['signal']}"
                )
            elif pattern["pattern_type"] == LEARNING_TYPE_AUDIT:
                improvements.append(
                    f"surface audit expectation {pattern['signal']}"
                )
            else:
                improvements.append(
                    f"preserve operational reference {pattern['signal']}"
                )
        return improvements

    def _validation_reasons(
        self,
        request: WorkflowLearningRequest,
        learning_type: str | None,
        checks: dict[str, bool],
        corrupt: list[dict[str, Any]],
        learning_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not learning_permitted:
            reasons.append("workflow_learning_not_permitted")
        if learning_type not in SUPPORTED_LEARNING_TYPES:
            reasons.append("unsupported_learning_type")
        if corrupt:
            reasons.append("corrupt_memory_blocks_learning")
        if request.governance_override_requested:
            reasons.append("governance_override_blocked")
        if self._critical_rule_change_requested(request):
            reasons.append("critical_rule_change_blocked")
        if self._governance_bypass_requested(request):
            reasons.append("governance_override_blocked")
        if not checks["governance_compliant"]:
            reasons.append("governance_compliance_required")
        if not checks["audit_consistent"]:
            reasons.append("audit_consistency_required")
        if request.reuse_requested and not checks["runtime_safe"]:
            reasons.append("runtime_safety_required_for_reuse")
        return self._unique(reasons)

    def _critical_rule_change_requested(
        self,
        request: WorkflowLearningRequest,
    ) -> bool:
        if request.allow_critical_rule_change:
            return True
        haystack = self._risk_text(request)
        critical_signals = (
            "critical_rule",
            "modify_critical",
            "change_critical",
            "alter_governance",
            "redefine_architecture",
            "autoevolve",
            "auto_expand_autonomy",
            "autoexpand_autonomy",
        )
        return any(signal in haystack for signal in critical_signals)

    def _governance_bypass_requested(
        self,
        request: WorkflowLearningRequest,
    ) -> bool:
        haystack = self._risk_text(request)
        bypass_signals = (
            "bypass_governance",
            "skip_governance",
            "ignore_audit",
            "skip_approval",
            "without_approval",
        )
        return any(signal in haystack for signal in bypass_signals)

    def _risk_text(self, request: WorkflowLearningRequest) -> str:
        values = [
            *request.detected_risks,
            *request.warnings,
            str(request.metadata),
        ]
        return " ".join(
            self._normalize(value) or "" for value in values if value
        )

    def _governance_status(
        self,
        request: WorkflowLearningRequest,
        records: list[dict[str, Any]],
    ) -> str | None:
        value = request.governance_status
        if value is None:
            value = next(
                (record.get("governance_status") for record in records if record.get("governance_status")),
                None,
            )
        return self._normalize(value)

    def _audit_status(
        self,
        request: WorkflowLearningRequest,
        records: list[dict[str, Any]],
    ) -> str | None:
        value = request.audit_status
        if value is None:
            value = next(
                (record.get("audit_status") for record in records if record.get("audit_status")),
                None,
            )
        return self._normalize(value)

    def _governance_compliant(
        self,
        request: WorkflowLearningRequest,
        governance_status: str | None,
    ) -> bool:
        if request.governance_override_requested:
            return False
        if request.reuse_requested:
            return governance_status in APPROVED_GOVERNANCE_STATUSES
        return True

    def _audit_consistent(
        self,
        request: WorkflowLearningRequest,
        audit_status: str | None,
    ) -> bool:
        if request.reuse_requested:
            return audit_status in APPROVED_AUDIT_STATUSES
        return True

    def _runtime_safe(self, request: WorkflowLearningRequest) -> bool:
        if not request.runtime_state:
            return not request.reuse_requested
        values = (
            request.runtime_state.get("state"),
            request.runtime_state.get("status"),
            request.runtime_state.get("loop_state"),
        )
        return any(self._normalize(value) in SAFE_RUNTIME_STATES for value in values)

    def _record_valid(self, record: dict[str, Any]) -> bool:
        return bool(
            record.get("memory_id")
            and record.get("memory_type")
            and record.get("timestamp")
            and isinstance(record.get("memory_context"), dict)
        )

    def _learning_type(self, value: str | None) -> str | None:
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
        if isinstance(value, OperationalMemoryResult):
            return value.to_dict().get("memory_record") or value.to_dict()
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
        learning_id: str,
        request: WorkflowLearningRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> WorkflowLearningResult:
        return self._result(
            status=LEARNING_STATUS_ERROR,
            success=False,
            learning_id=learning_id,
            request=request,
            learning_type=self._learning_type(request.learning_type),
            pattern_type=None,
            learning_status=LEARNING_STATUS_ERROR,
            governance_status=request.governance_status,
            audit_status=request.audit_status,
            optimization_status="blocked",
            checks={
                "governance_compliant": False,
                "audit_consistent": False,
                "runtime_safe": False,
                "context_safe": False,
            },
            reuse_allowed=False,
            memory_analyzed=False,
            learning_validated=False,
            patterns=[],
            insights=[],
            improvements=[],
            recurrent_errors=[],
            audit_expectations=[],
            records=[],
            lifecycle=(self._lifecycle(LEARNING_STATUS_ERROR),),
            reasons=["workflow_learning_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _publish(self, result: WorkflowLearningResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_workflow_learning_result",
        ):
            self.status.mark_workflow_learning_result(result.to_dict())

    def _log_result(self, result: WorkflowLearningResult) -> None:
        if result.status == LEARNING_STATUS_ERROR:
            logger.error(
                "workflow_learning: error learning_id=%s error=%s",
                result.learning_id,
                result.error,
            )
            return
        if result.status == LEARNING_STATUS_BLOCKED:
            logger.warning(
                "workflow_learning: blocked learning_id=%s reasons=%s",
                result.learning_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "workflow_learning: %s learning_id=%s type=%s patterns=%s",
            result.status,
            result.learning_id,
            result.learning_type,
            len(result.patterns_detected),
        )
