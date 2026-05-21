"""
Controlled audit request system for Hermes runtime.

This layer creates formal audit requests from self-validation context, freezes
continuation, preserves traceability, and prepares external delivery. It does
not approve audits, modify audit results, call external auditors, mutate tasks,
or continue execution automatically.
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

from app.runner.self_validation import SelfValidationResult

logger = logging.getLogger(__name__)

AUDIT_TYPE_EXECUTION = "execution"
AUDIT_TYPE_FILE = "file"
AUDIT_TYPE_ARCHITECTURE = "architecture"
AUDIT_TYPE_SECURITY = "security"
AUDIT_TYPE_OPERATIONAL = "operational"
SUPPORTED_AUDIT_TYPES = {
    AUDIT_TYPE_EXECUTION,
    AUDIT_TYPE_FILE,
    AUDIT_TYPE_ARCHITECTURE,
    AUDIT_TYPE_SECURITY,
    AUDIT_TYPE_OPERATIONAL,
}

AUDIT_STATE_REQUESTED = "requested"
AUDIT_STATE_PENDING = "pending"
AUDIT_STATE_UNDER_REVIEW = "under_review"
AUDIT_STATE_APPROVED = "approved"
AUDIT_STATE_REJECTED = "rejected"
AUDIT_STATE_NEEDS_FIX = "needs_fix"

AUDIT_STATUS_BLOCKED = "blocked"
AUDIT_STATUS_ERROR = "error"

DEFAULT_AUDIT_TARGETS = ("sentinel",)


@dataclass(frozen=True)
class AuditRequestInput:
    execution_id: str | None = None
    task_id: str | None = None
    audit_type: str | None = None
    validation_result: SelfValidationResult | Any | None = None
    audit_package: dict[str, Any] = field(default_factory=dict)
    execution_summary: str = ""
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    execution_logs: tuple[Any, ...] = field(default_factory=tuple)
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    provider_context: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    delivery_targets: tuple[str, ...] = DEFAULT_AUDIT_TARGETS
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditRequestResult:
    status: str
    success: bool
    audit_id: str
    execution_id: str | None
    task_id: str | None
    audit_type: str
    audit_status: str
    validation_status: str | None
    risk_status: str | None
    audit_package: dict[str, Any]
    audit_package_hash: str | None
    continuation_frozen: bool
    continuation_status: str
    traceability_preserved: bool
    delivery_targets: tuple[str, ...] = field(default_factory=tuple)
    delivery_status: str = "not_prepared"
    audit_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    provider_context: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
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
            "audit_id": self.audit_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "audit_type": self.audit_type,
            "audit_status": self.audit_status,
            "validation_status": self.validation_status,
            "risk_status": self.risk_status,
            "audit_package": dict(self.audit_package),
            "audit_package_hash": self.audit_package_hash,
            "continuation_frozen": self.continuation_frozen,
            "continuation_status": self.continuation_status,
            "traceability_preserved": self.traceability_preserved,
            "delivery_targets": list(self.delivery_targets),
            "delivery_status": self.delivery_status,
            "audit_lifecycle": [
                dict(entry) for entry in self.audit_lifecycle
            ],
            "modified_files": list(self.modified_files),
            "detected_risks": list(self.detected_risks),
            "provider_context": dict(self.provider_context),
            "runtime_state": dict(self.runtime_state),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class AuditRequestSystem:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def request(
        self,
        request: AuditRequestInput,
        runtime_active: bool = True,
        audit_permitted: bool = True,
    ) -> AuditRequestResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        audit_id = str(uuid4())

        try:
            validation = self._validation_result(request.validation_result)
            audit_package = self._audit_package(request, validation)
            audit_type = self._audit_type(request, validation, audit_package)
            reasons = self._request_reasons(
                request=request,
                validation=validation,
                audit_package=audit_package,
                audit_type=audit_type,
                runtime_active=runtime_active,
                audit_permitted=audit_permitted,
            )
            if reasons:
                result = self._blocked_result(
                    request=request,
                    validation=validation,
                    audit_package=audit_package,
                    audit_id=audit_id,
                    audit_type=audit_type,
                    reasons=reasons,
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            lifecycle = (
                self._lifecycle(AUDIT_STATE_REQUESTED),
                self._lifecycle(AUDIT_STATE_PENDING),
            )
            result = self._result(
                status=AUDIT_STATE_PENDING,
                success=True,
                request=request,
                validation=validation,
                audit_id=audit_id,
                audit_type=audit_type,
                audit_status=AUDIT_STATE_PENDING,
                audit_package=audit_package,
                continuation_frozen=True,
                continuation_status="frozen_waiting_audit",
                traceability_preserved=True,
                delivery_targets=self._delivery_targets(request),
                delivery_status="prepared",
                audit_lifecycle=lifecycle,
                reasons=[],
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                status=AUDIT_STATUS_ERROR,
                success=False,
                request=request,
                validation={},
                audit_id=audit_id,
                audit_type=AUDIT_TYPE_OPERATIONAL,
                audit_status=AUDIT_STATUS_ERROR,
                audit_package={},
                continuation_frozen=True,
                continuation_status="frozen_audit_error",
                traceability_preserved=True,
                delivery_targets=tuple(),
                delivery_status="blocked",
                audit_lifecycle=(self._lifecycle(AUDIT_STATUS_ERROR),),
                reasons=["audit_request_error_contained"],
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _blocked_result(
        self,
        request: AuditRequestInput,
        validation: dict[str, Any],
        audit_package: dict[str, Any],
        audit_id: str,
        audit_type: str,
        reasons: list[str],
        started: float,
        started_at: datetime,
    ) -> AuditRequestResult:
        return self._result(
            status=AUDIT_STATUS_BLOCKED,
            success=False,
            request=request,
            validation=validation,
            audit_id=audit_id,
            audit_type=audit_type,
            audit_status=AUDIT_STATUS_BLOCKED,
            audit_package=audit_package,
            continuation_frozen=True,
            continuation_status="frozen_audit_blocked",
            traceability_preserved=True,
            delivery_targets=self._delivery_targets(request),
            delivery_status="blocked",
            audit_lifecycle=(self._lifecycle(AUDIT_STATUS_BLOCKED),),
            reasons=reasons,
            error=";".join(reasons),
            started=started,
            started_at=started_at,
        )

    def _result(
        self,
        status: str,
        success: bool,
        request: AuditRequestInput,
        validation: dict[str, Any],
        audit_id: str,
        audit_type: str,
        audit_status: str,
        audit_package: dict[str, Any],
        continuation_frozen: bool,
        continuation_status: str,
        traceability_preserved: bool,
        delivery_targets: tuple[str, ...],
        delivery_status: str,
        audit_lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> AuditRequestResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        execution_id = (
            request.execution_id
            or validation.get("execution_id")
            or audit_package.get("execution_id")
        )
        task_id = (
            request.task_id
            or validation.get("task_id")
            or audit_package.get("task_id")
        )
        modified_files = self._modified_files(request, validation, audit_package)
        detected_risks = self._detected_risks(request, validation, audit_package)
        return AuditRequestResult(
            status=status,
            success=success,
            audit_id=audit_id,
            execution_id=execution_id,
            task_id=task_id,
            audit_type=audit_type,
            audit_status=audit_status,
            validation_status=validation.get("validation_status"),
            risk_status=validation.get("risk_status"),
            audit_package=dict(audit_package),
            audit_package_hash=self._hash_package(audit_package),
            continuation_frozen=continuation_frozen,
            continuation_status=continuation_status,
            traceability_preserved=traceability_preserved,
            delivery_targets=delivery_targets,
            delivery_status=delivery_status,
            audit_lifecycle=audit_lifecycle,
            modified_files=tuple(modified_files),
            detected_risks=tuple(detected_risks),
            provider_context=dict(request.provider_context or {}),
            runtime_state=dict(request.runtime_state or {}),
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _request_reasons(
        self,
        request: AuditRequestInput,
        validation: dict[str, Any],
        audit_package: dict[str, Any],
        audit_type: str,
        runtime_active: bool,
        audit_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        execution_id = (
            request.execution_id
            or validation.get("execution_id")
            or audit_package.get("execution_id")
        )
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not audit_permitted:
            reasons.append("audit_request_not_permitted")
        if not execution_id:
            reasons.append("missing_execution_id")
        if audit_type not in SUPPORTED_AUDIT_TYPES:
            reasons.append("unsupported_audit_type")
        if not validation.get("validation_status"):
            reasons.append("missing_validation_status")
        if not validation.get("risk_status"):
            reasons.append("missing_risk_status")
        if not audit_package:
            reasons.append("missing_audit_package")
        if not self._delivery_targets(request):
            reasons.append("missing_audit_delivery_target")
        return self._unique(reasons)

    def _audit_package(
        self,
        request: AuditRequestInput,
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        package = dict(request.audit_package or {})
        validation_package = validation.get("audit_package")
        if not package and isinstance(validation_package, dict):
            package = dict(validation_package)
        if not package:
            return {}
        package.setdefault("execution_id", request.execution_id or validation.get("execution_id"))
        package.setdefault("task_id", request.task_id or validation.get("task_id"))
        package.setdefault("modified_files", list(request.modified_files) or validation.get("modified_files") or [])
        package.setdefault("detected_risks", list(request.detected_risks) or validation.get("detected_risks") or [])
        package.setdefault("execution_logs", [self._as_dict(log) for log in request.execution_logs])
        package.setdefault("provider_context", dict(request.provider_context or {}))
        package.setdefault("runtime_state", dict(request.runtime_state or {}))
        package.setdefault("execution_summary", request.execution_summary)
        package.setdefault("delivery_prepared_for", list(self._delivery_targets(request)))
        package.setdefault("audit_requested_at", datetime.now(timezone.utc).isoformat())
        return package

    def _audit_type(
        self,
        request: AuditRequestInput,
        validation: dict[str, Any],
        audit_package: dict[str, Any],
    ) -> str:
        if request.audit_type in SUPPORTED_AUDIT_TYPES:
            return str(request.audit_type)
        risks = " ".join(self._detected_risks(request, validation, audit_package)).lower()
        files = " ".join(self._modified_files(request, validation, audit_package)).lower()
        package_text = json.dumps(audit_package, sort_keys=True, default=str).lower()
        if any(
            word in f"{risks} {package_text}"
            for word in ("security", "secret", "credential")
        ):
            return AUDIT_TYPE_SECURITY
        if any(word in files for word in ("architecture", "runtime_loop", "core")):
            return AUDIT_TYPE_ARCHITECTURE
        if files:
            return AUDIT_TYPE_FILE
        if validation.get("risk_status") in {"critical", "elevated"}:
            return AUDIT_TYPE_OPERATIONAL
        return AUDIT_TYPE_EXECUTION

    def _validation_result(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, SelfValidationResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _modified_files(
        self,
        request: AuditRequestInput,
        validation: dict[str, Any],
        audit_package: dict[str, Any],
    ) -> list[str]:
        files = [
            *[str(path) for path in request.modified_files],
            *[str(path) for path in validation.get("modified_files") or []],
            *[str(path) for path in audit_package.get("modified_files") or []],
        ]
        return self._unique(files)

    def _detected_risks(
        self,
        request: AuditRequestInput,
        validation: dict[str, Any],
        audit_package: dict[str, Any],
    ) -> list[str]:
        risks = [
            *[str(risk) for risk in request.detected_risks],
            *[str(risk) for risk in validation.get("detected_risks") or []],
            *[str(risk) for risk in audit_package.get("detected_risks") or []],
        ]
        return self._unique(risks)

    def _delivery_targets(self, request: AuditRequestInput) -> tuple[str, ...]:
        return tuple(str(target) for target in request.delivery_targets if target)

    def _hash_package(self, package: dict[str, Any]) -> str | None:
        if not package:
            return None
        body = json.dumps(package, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(body).hexdigest()

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
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

    def _publish(self, result: AuditRequestResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_audit_request_result",
        ):
            self.status.mark_audit_request_result(result.to_dict())

    def _log_result(self, result: AuditRequestResult) -> None:
        if result.success:
            logger.info(
                "audit_request: pending audit_id=%s execution_id=%s type=%s targets=%s",
                result.audit_id,
                result.execution_id,
                result.audit_type,
                ",".join(result.delivery_targets),
            )
            return
        if result.status == AUDIT_STATUS_ERROR:
            logger.error(
                "audit_request: error audit_id=%s error=%s",
                result.audit_id,
                result.error,
            )
            return
        logger.warning(
            "audit_request: blocked audit_id=%s reasons=%s",
            result.audit_id,
            ",".join(result.reasons),
        )
