"""
Controlled audit response handling for Hermes runtime.

This layer receives official audit results, validates their integrity,
preserves execution context, and decides whether continuation remains blocked
or can move to the human approval pipeline. It does not modify audit results,
call external auditors, mutate tasks, approve work, or continue execution.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.audit_request_system import AuditRequestResult

logger = logging.getLogger(__name__)

AUDIT_RESULT_APPROVED = "approved"
AUDIT_RESULT_APPROVED_WITH_WARNINGS = "approved_with_warnings"
AUDIT_RESULT_NEEDS_FIX = "needs_fix"
AUDIT_RESULT_REJECTED = "rejected"
SUPPORTED_AUDIT_RESULTS = {
    AUDIT_RESULT_APPROVED,
    AUDIT_RESULT_APPROVED_WITH_WARNINGS,
    AUDIT_RESULT_NEEDS_FIX,
    AUDIT_RESULT_REJECTED,
}

AUDIT_RESPONSE_BLOCKED = "blocked"
AUDIT_RESPONSE_ERROR = "error"

RISK_LEVEL_CLEAR = "clear"
RISK_LEVEL_LOW = "low"
RISK_LEVEL_ELEVATED = "elevated"
RISK_LEVEL_CRITICAL = "critical"

SECURITY_ESCALATION_HINTS = (
    "malicious",
    "security",
    "secret",
    "credential",
    "leak",
    "runtime compromise",
    "filesystem danger",
    "unauthorized execution",
    "infrastructure threat",
    "destructive",
)

OFFICIAL_AUDITORS = {"sentinel", "centinela"}


@dataclass(frozen=True)
class AuditResponseInput:
    audit_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    audit_result: str | None = None
    risk_level: str | None = None
    auditor: str = "sentinel"
    audit_request: AuditRequestResult | dict[str, Any] | Any | None = None
    audit_response: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    rejection_reasons: tuple[str, ...] = field(default_factory=tuple)
    correction_requirements: tuple[str, ...] = field(default_factory=tuple)
    execution_context: dict[str, Any] = field(default_factory=dict)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    audit_logs: tuple[Any, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditResponseControlResult:
    status: str
    success: bool
    response_id: str
    audit_id: str | None
    execution_id: str | None
    task_id: str | None
    audit_result: str | None
    risk_level: str | None
    correction_status: str
    continuation_status: str
    human_approval_status: str
    security_escalation_status: str
    centinela_escalation: bool
    execution_decision: str
    context_preserved: bool
    audit_integrity_preserved: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    rejection_reasons: tuple[str, ...] = field(default_factory=tuple)
    correction_requirements: tuple[str, ...] = field(default_factory=tuple)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    audit_logs: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    audit_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    execution_context: dict[str, Any] = field(default_factory=dict)
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
            "response_id": self.response_id,
            "audit_id": self.audit_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "audit_result": self.audit_result,
            "risk_level": self.risk_level,
            "correction_status": self.correction_status,
            "continuation_status": self.continuation_status,
            "human_approval_status": self.human_approval_status,
            "security_escalation_status": self.security_escalation_status,
            "centinela_escalation": self.centinela_escalation,
            "execution_decision": self.execution_decision,
            "context_preserved": self.context_preserved,
            "audit_integrity_preserved": self.audit_integrity_preserved,
            "warnings": list(self.warnings),
            "detected_risks": list(self.detected_risks),
            "rejection_reasons": list(self.rejection_reasons),
            "correction_requirements": list(self.correction_requirements),
            "modified_files": list(self.modified_files),
            "audit_logs": [dict(entry) for entry in self.audit_logs],
            "audit_lifecycle": [
                dict(entry) for entry in self.audit_lifecycle
            ],
            "execution_context": dict(self.execution_context),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class AuditResponseControl:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def process(
        self,
        request: AuditResponseInput,
        runtime_active: bool = True,
        response_permitted: bool = True,
    ) -> AuditResponseControlResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        response_id = str(uuid4())

        try:
            audit_request = self._audit_request(request.audit_request)
            response = self._audit_response(request)
            audit_result = self._audit_result(request, response)
            risk_level = self._risk_level(request, response, audit_request)
            audit_id = self._audit_id(request, response, audit_request)
            execution_id = self._execution_id(request, response, audit_request)
            task_id = self._task_id(request, response, audit_request)
            reasons = self._validation_reasons(
                request=request,
                audit_request=audit_request,
                audit_result=audit_result,
                risk_level=risk_level,
                audit_id=audit_id,
                execution_id=execution_id,
                runtime_active=runtime_active,
                response_permitted=response_permitted,
            )

            if reasons:
                result = self._result(
                    status=AUDIT_RESPONSE_BLOCKED,
                    success=False,
                    response_id=response_id,
                    audit_id=audit_id,
                    execution_id=execution_id,
                    task_id=task_id,
                    audit_result=audit_result,
                    risk_level=risk_level,
                    correction_status="blocked",
                    continuation_status="blocked_audit_response_invalid",
                    human_approval_status="blocked",
                    security_escalation_status="not_evaluated",
                    centinela_escalation=False,
                    execution_decision="block_invalid_audit_response",
                    context_preserved=True,
                    audit_integrity_preserved=False,
                    request=request,
                    audit_request=audit_request,
                    audit_response=response,
                    audit_lifecycle=(
                        self._lifecycle("received"),
                        self._lifecycle(AUDIT_RESPONSE_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            centinela_escalation = self._requires_security_escalation(
                request=request,
                audit_request=audit_request,
                audit_response=response,
                audit_result=audit_result,
                risk_level=risk_level,
            )
            decision = self._decision(audit_result, centinela_escalation)
            lifecycle = (
                self._lifecycle("received"),
                self._lifecycle("validated"),
                self._lifecycle(audit_result or AUDIT_RESPONSE_BLOCKED),
            )
            result = self._result(
                status=audit_result or AUDIT_RESPONSE_BLOCKED,
                success=bool(decision["success"]),
                response_id=response_id,
                audit_id=audit_id,
                execution_id=execution_id,
                task_id=task_id,
                audit_result=audit_result,
                risk_level=risk_level,
                correction_status=str(decision["correction_status"]),
                continuation_status=str(decision["continuation_status"]),
                human_approval_status=str(decision["human_approval_status"]),
                security_escalation_status=str(
                    decision["security_escalation_status"]
                ),
                centinela_escalation=centinela_escalation,
                execution_decision=str(decision["execution_decision"]),
                context_preserved=True,
                audit_integrity_preserved=True,
                request=request,
                audit_request=audit_request,
                audit_response=response,
                audit_lifecycle=lifecycle,
                reasons=list(decision["reasons"]),
                error=None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                status=AUDIT_RESPONSE_ERROR,
                success=False,
                response_id=response_id,
                audit_id=request.audit_id,
                execution_id=request.execution_id,
                task_id=request.task_id,
                audit_result=request.audit_result,
                risk_level=request.risk_level,
                correction_status="blocked",
                continuation_status="blocked_audit_response_error",
                human_approval_status="blocked",
                security_escalation_status="not_evaluated",
                centinela_escalation=False,
                execution_decision="block_audit_response_error",
                context_preserved=True,
                audit_integrity_preserved=False,
                request=request,
                audit_request={},
                audit_response={},
                audit_lifecycle=(self._lifecycle(AUDIT_RESPONSE_ERROR),),
                reasons=["audit_response_error_contained"],
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
        response_id: str,
        audit_id: str | None,
        execution_id: str | None,
        task_id: str | None,
        audit_result: str | None,
        risk_level: str | None,
        correction_status: str,
        continuation_status: str,
        human_approval_status: str,
        security_escalation_status: str,
        centinela_escalation: bool,
        execution_decision: str,
        context_preserved: bool,
        audit_integrity_preserved: bool,
        request: AuditResponseInput,
        audit_request: dict[str, Any],
        audit_response: dict[str, Any],
        audit_lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> AuditResponseControlResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return AuditResponseControlResult(
            status=status,
            success=success,
            response_id=response_id,
            audit_id=audit_id,
            execution_id=execution_id,
            task_id=task_id,
            audit_result=audit_result,
            risk_level=risk_level,
            correction_status=correction_status,
            continuation_status=continuation_status,
            human_approval_status=human_approval_status,
            security_escalation_status=security_escalation_status,
            centinela_escalation=centinela_escalation,
            execution_decision=execution_decision,
            context_preserved=context_preserved,
            audit_integrity_preserved=audit_integrity_preserved,
            warnings=tuple(self._warnings(request, audit_response)),
            detected_risks=tuple(
                self._detected_risks(request, audit_request, audit_response)
            ),
            rejection_reasons=tuple(
                self._rejection_reasons(request, audit_response)
            ),
            correction_requirements=tuple(
                self._correction_requirements(request, audit_response)
            ),
            modified_files=tuple(self._modified_files(request, audit_request)),
            audit_logs=tuple(self._audit_logs(request, audit_response)),
            audit_lifecycle=audit_lifecycle,
            execution_context=dict(request.execution_context or {}),
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: AuditResponseInput,
        audit_request: dict[str, Any],
        audit_result: str | None,
        risk_level: str | None,
        audit_id: str | None,
        execution_id: str | None,
        runtime_active: bool,
        response_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        auditor = str(request.auditor or "").strip().lower()
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not response_permitted:
            reasons.append("audit_response_not_permitted")
        if not audit_id:
            reasons.append("missing_audit_id")
        if not execution_id:
            reasons.append("missing_execution_id")
        if not auditor:
            reasons.append("missing_auditor")
        elif auditor not in OFFICIAL_AUDITORS:
            reasons.append("unsupported_auditor")
        if audit_result not in SUPPORTED_AUDIT_RESULTS:
            reasons.append("unsupported_audit_result")
        if not risk_level:
            reasons.append("missing_risk_level")
        reasons.extend(
            self._integrity_reasons(
                audit_request=audit_request,
                audit_id=audit_id,
                execution_id=execution_id,
            )
        )
        return self._unique(reasons)

    def _integrity_reasons(
        self,
        audit_request: dict[str, Any],
        audit_id: str | None,
        execution_id: str | None,
    ) -> list[str]:
        if not audit_request:
            return []
        reasons: list[str] = []
        request_audit_id = audit_request.get("audit_id")
        request_execution_id = audit_request.get("execution_id")
        if request_audit_id and audit_id and request_audit_id != audit_id:
            reasons.append("audit_id_mismatch")
        if (
            request_execution_id
            and execution_id
            and request_execution_id != execution_id
        ):
            reasons.append("execution_id_mismatch")
        package = audit_request.get("audit_package")
        expected_hash = audit_request.get("audit_package_hash")
        if isinstance(package, dict) and expected_hash:
            actual_hash = self._hash_package(package)
            if actual_hash != expected_hash:
                reasons.append("audit_package_integrity_mismatch")
        return reasons

    def _decision(
        self,
        audit_result: str | None,
        centinela_escalation: bool,
    ) -> dict[str, Any]:
        if centinela_escalation:
            return {
                "success": False,
                "correction_status": "blocked",
                "continuation_status": "blocked_security_escalation",
                "human_approval_status": "escalated",
                "security_escalation_status": "escalated_to_centinela",
                "execution_decision": "escalate_to_centinela",
                "reasons": ["critical_security_escalation_required"],
            }
        if audit_result == AUDIT_RESULT_APPROVED:
            return {
                "success": True,
                "correction_status": "not_required",
                "continuation_status": "ready_for_approval_pipeline",
                "human_approval_status": "pending",
                "security_escalation_status": "not_required",
                "execution_decision": "continue_to_approval_pipeline",
                "reasons": [],
            }
        if audit_result == AUDIT_RESULT_APPROVED_WITH_WARNINGS:
            return {
                "success": True,
                "correction_status": "not_required",
                "continuation_status": "ready_with_warnings",
                "human_approval_status": "pending",
                "security_escalation_status": "not_required",
                "execution_decision": "continue_with_human_visibility",
                "reasons": ["approved_with_warnings"],
            }
        if audit_result == AUDIT_RESULT_NEEDS_FIX:
            return {
                "success": False,
                "correction_status": "required",
                "continuation_status": "blocked_needs_fix",
                "human_approval_status": "blocked",
                "security_escalation_status": "not_required",
                "execution_decision": "prepare_correction_workflow",
                "reasons": ["correction_required"],
            }
        return {
            "success": False,
            "correction_status": "blocked",
            "continuation_status": "blocked_rejected",
            "human_approval_status": "escalated",
            "security_escalation_status": "not_required",
            "execution_decision": "escalate_to_human",
            "reasons": ["audit_rejected"],
        }

    def _requires_security_escalation(
        self,
        request: AuditResponseInput,
        audit_request: dict[str, Any],
        audit_response: dict[str, Any],
        audit_result: str | None,
        risk_level: str | None,
    ) -> bool:
        text = " ".join(
            [
                *self._detected_risks(request, audit_request, audit_response),
                *self._rejection_reasons(request, audit_response),
                *self._correction_requirements(request, audit_response),
                json.dumps(audit_request, sort_keys=True, default=str),
                json.dumps(audit_response, sort_keys=True, default=str),
            ]
        ).lower()
        request_type = str(audit_request.get("audit_type") or "").lower()
        has_security_hint = any(hint in text for hint in SECURITY_ESCALATION_HINTS)
        if request_type == "security" and risk_level == RISK_LEVEL_CRITICAL:
            return True
        if risk_level == RISK_LEVEL_CRITICAL and has_security_hint:
            return True
        if audit_result == AUDIT_RESULT_REJECTED and has_security_hint:
            return True
        return False

    def _audit_response(self, request: AuditResponseInput) -> dict[str, Any]:
        response = dict(request.audit_response or {})
        response.setdefault("audit_id", request.audit_id)
        response.setdefault("execution_id", request.execution_id)
        response.setdefault("task_id", request.task_id)
        response.setdefault("audit_result", request.audit_result)
        response.setdefault("risk_level", request.risk_level)
        response.setdefault("auditor", request.auditor)
        response.setdefault("warnings", list(request.warnings))
        response.setdefault("detected_risks", list(request.detected_risks))
        response.setdefault("rejection_reasons", list(request.rejection_reasons))
        response.setdefault(
            "correction_requirements",
            list(request.correction_requirements),
        )
        response.setdefault("received_at", datetime.now(timezone.utc).isoformat())
        return response

    def _audit_request(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, AuditRequestResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _audit_result(
        self,
        request: AuditResponseInput,
        response: dict[str, Any],
    ) -> str | None:
        value = request.audit_result or response.get("audit_result")
        if value is None:
            return None
        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"warning", "approved_warning", "approved_warnings"}:
            return AUDIT_RESULT_APPROVED_WITH_WARNINGS
        return normalized

    def _risk_level(
        self,
        request: AuditResponseInput,
        response: dict[str, Any],
        audit_request: dict[str, Any],
    ) -> str | None:
        value = (
            request.risk_level
            or response.get("risk_level")
            or audit_request.get("risk_status")
        )
        if value is None:
            return None
        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"none", "ok", "safe"}:
            return RISK_LEVEL_CLEAR
        if normalized in {"minor", "warning", "warnings"}:
            return RISK_LEVEL_LOW
        if normalized in {"medium", "moderate"}:
            return RISK_LEVEL_ELEVATED
        if normalized in {"severe", "high"}:
            return RISK_LEVEL_CRITICAL
        return normalized

    def _audit_id(
        self,
        request: AuditResponseInput,
        response: dict[str, Any],
        audit_request: dict[str, Any],
    ) -> str | None:
        return (
            request.audit_id
            or response.get("audit_id")
            or audit_request.get("audit_id")
        )

    def _execution_id(
        self,
        request: AuditResponseInput,
        response: dict[str, Any],
        audit_request: dict[str, Any],
    ) -> str | None:
        return (
            request.execution_id
            or response.get("execution_id")
            or audit_request.get("execution_id")
        )

    def _task_id(
        self,
        request: AuditResponseInput,
        response: dict[str, Any],
        audit_request: dict[str, Any],
    ) -> str | None:
        return (
            request.task_id
            or response.get("task_id")
            or audit_request.get("task_id")
        )

    def _warnings(
        self,
        request: AuditResponseInput,
        audit_response: dict[str, Any],
    ) -> list[str]:
        return self._unique(
            [
                *[str(item) for item in request.warnings],
                *[str(item) for item in audit_response.get("warnings") or []],
            ]
        )

    def _detected_risks(
        self,
        request: AuditResponseInput,
        audit_request: dict[str, Any],
        audit_response: dict[str, Any],
    ) -> list[str]:
        request_package = audit_request.get("audit_package") or {}
        return self._unique(
            [
                *[str(item) for item in request.detected_risks],
                *[
                    str(item)
                    for item in audit_response.get("detected_risks") or []
                ],
                *[str(item) for item in audit_request.get("detected_risks") or []],
                *[str(item) for item in request_package.get("detected_risks") or []],
            ]
        )

    def _rejection_reasons(
        self,
        request: AuditResponseInput,
        audit_response: dict[str, Any],
    ) -> list[str]:
        return self._unique(
            [
                *[str(item) for item in request.rejection_reasons],
                *[
                    str(item)
                    for item in audit_response.get("rejection_reasons") or []
                ],
            ]
        )

    def _correction_requirements(
        self,
        request: AuditResponseInput,
        audit_response: dict[str, Any],
    ) -> list[str]:
        return self._unique(
            [
                *[str(item) for item in request.correction_requirements],
                *[
                    str(item)
                    for item in audit_response.get("correction_requirements")
                    or []
                ],
            ]
        )

    def _modified_files(
        self,
        request: AuditResponseInput,
        audit_request: dict[str, Any],
    ) -> list[str]:
        request_package = audit_request.get("audit_package") or {}
        return self._unique(
            [
                *[str(path) for path in request.modified_files],
                *[str(path) for path in audit_request.get("modified_files") or []],
                *[str(path) for path in request_package.get("modified_files") or []],
            ]
        )

    def _audit_logs(
        self,
        request: AuditResponseInput,
        audit_response: dict[str, Any],
    ) -> list[dict[str, Any]]:
        logs = [
            *[self._as_dict(entry) for entry in request.audit_logs],
            *[
                self._as_dict(entry)
                for entry in audit_response.get("audit_logs") or []
            ],
        ]
        if logs:
            return logs
        return [
            {
                "event": "audit_response_received",
                "audit_result": audit_response.get("audit_result"),
                "at": datetime.now(timezone.utc).isoformat(),
            }
        ]

    def _hash_package(self, package: dict[str, Any]) -> str:
        body = json.dumps(package, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(body).hexdigest()

    def _as_dict(self, value: Any) -> dict[str, Any]:
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

    def _publish(self, result: AuditResponseControlResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_audit_response_result",
        ):
            self.status.mark_audit_response_result(result.to_dict())

    def _log_result(self, result: AuditResponseControlResult) -> None:
        if result.status == AUDIT_RESPONSE_ERROR:
            logger.error(
                "audit_response: error response_id=%s error=%s",
                result.response_id,
                result.error,
            )
            return
        if result.status == AUDIT_RESPONSE_BLOCKED:
            logger.warning(
                "audit_response: blocked response_id=%s reasons=%s",
                result.response_id,
                ",".join(result.reasons),
            )
            return
        if result.success:
            logger.info(
                "audit_response: accepted response_id=%s audit_id=%s result=%s",
                result.response_id,
                result.audit_id,
                result.audit_result,
            )
            return
        logger.warning(
            "audit_response: continuation_blocked response_id=%s result=%s reasons=%s",
            result.response_id,
            result.audit_result,
            ",".join(result.reasons),
        )
