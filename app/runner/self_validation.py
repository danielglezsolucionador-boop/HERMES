"""
Controlled self-validation for Hermes execution runtime.

This layer performs deterministic checks over outputs, modified files, runtime
state, lifecycle signals, risks, and provider responses before external audit.
It does not approve critical work, replace audit, call providers, retry,
recover, mutate tasks, or persist data.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

VALIDATION_STATUS_VALID = "valid"
VALIDATION_STATUS_WARNING = "warning"
VALIDATION_STATUS_INVALID = "invalid"
VALIDATION_STATUS_ERROR = "error"

RISK_STATUS_CLEAR = "clear"
RISK_STATUS_ELEVATED = "elevated"
RISK_STATUS_CRITICAL = "critical"

VALIDATION_TYPE_EXECUTION = "execution"
VALIDATION_TYPE_FILE = "file"
VALIDATION_TYPE_RUNTIME = "runtime"
VALIDATION_TYPE_RISK = "risk"
VALIDATION_TYPE_RESPONSE = "response"

RUNTIME_CORE_HINTS = (
    "runtime_loop",
    "polling",
    "task_runner",
    "recovery",
)
SEVERE_RISK_HINTS = (
    "corrupt",
    "data_loss",
    "security",
    "secret",
    "critical",
    "unsafe",
)


@dataclass(frozen=True)
class SelfValidationRequest:
    execution_id: str | None = None
    task_id: str | None = None
    outputs: tuple[str, ...] = field(default_factory=tuple)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    execution_logs: tuple[Any, ...] = field(default_factory=tuple)
    provider_responses: tuple[Any, ...] = field(default_factory=tuple)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    lifecycle_state: dict[str, Any] = field(default_factory=dict)
    risk_notes: tuple[str, ...] = field(default_factory=tuple)
    expected_outputs: tuple[str, ...] = field(default_factory=tuple)
    critical_change: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SelfValidationResult:
    status: str
    success: bool
    validation_id: str
    execution_id: str | None
    task_id: str | None
    validation_status: str
    risk_status: str
    audit_required: bool
    self_approved: bool
    continuation_blocked: bool
    runtime_protected: bool
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    validation_logs: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    inconsistencies: tuple[str, ...] = field(default_factory=tuple)
    audit_package: dict[str, Any] = field(default_factory=dict)
    output_count: int = 0
    response_count: int = 0
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
            "validation_id": self.validation_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "validation_status": self.validation_status,
            "risk_status": self.risk_status,
            "audit_required": self.audit_required,
            "self_approved": self.self_approved,
            "continuation_blocked": self.continuation_blocked,
            "runtime_protected": self.runtime_protected,
            "modified_files": list(self.modified_files),
            "validation_logs": [dict(log) for log in self.validation_logs],
            "detected_risks": list(self.detected_risks),
            "inconsistencies": list(self.inconsistencies),
            "audit_package": dict(self.audit_package),
            "output_count": self.output_count,
            "response_count": self.response_count,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class SelfValidation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def validate(
        self,
        request: SelfValidationRequest,
        runtime_active: bool = True,
        validation_permitted: bool = True,
    ) -> SelfValidationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        validation_id = str(uuid4())

        try:
            logs: list[dict[str, Any]] = []
            warnings: list[str] = []
            invalid: list[str] = []
            risks: list[str] = []

            invalid.extend(
                self._execution_reasons(
                    request=request,
                    runtime_active=runtime_active,
                    validation_permitted=validation_permitted,
                    logs=logs,
                )
            )
            file_reasons, file_risks = self._file_reasons(request, logs)
            invalid.extend(file_reasons)
            risks.extend(file_risks)
            runtime_reasons, runtime_warnings = self._runtime_reasons(
                request,
                logs,
            )
            invalid.extend(runtime_reasons)
            warnings.extend(runtime_warnings)
            risk_reasons, risk_warnings = self._risk_reasons(request, logs)
            invalid.extend(risk_reasons)
            warnings.extend(risk_warnings)
            response_reasons, response_warnings = self._response_reasons(
                request,
                logs,
            )
            invalid.extend(response_reasons)
            warnings.extend(response_warnings)

            invalid = self._unique(invalid)
            warnings = self._unique(warnings)
            risks = self._unique([*risks, *risk_warnings])
            validation_status = self._validation_status(invalid, [*warnings, *risks])
            risk_status = self._risk_status(invalid, risks)
            continuation_blocked = validation_status == VALIDATION_STATUS_INVALID
            audit_package = self._audit_package(
                validation_id=validation_id,
                request=request,
                validation_status=validation_status,
                risk_status=risk_status,
                validation_logs=logs,
                detected_risks=risks,
                inconsistencies=invalid,
                warnings=warnings,
            )
            result = self._result(
                status=validation_status,
                success=validation_status != VALIDATION_STATUS_INVALID,
                validation_id=validation_id,
                request=request,
                validation_status=validation_status,
                risk_status=risk_status,
                audit_required=True,
                continuation_blocked=continuation_blocked,
                validation_logs=logs,
                detected_risks=risks,
                inconsistencies=invalid,
                audit_package=audit_package,
                reasons=[*invalid, *warnings, *risks],
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                status=VALIDATION_STATUS_ERROR,
                success=False,
                validation_id=validation_id,
                request=request,
                validation_status=VALIDATION_STATUS_ERROR,
                risk_status=RISK_STATUS_CRITICAL,
                audit_required=True,
                continuation_blocked=True,
                validation_logs=(
                    self._log(
                        VALIDATION_TYPE_RUNTIME,
                        VALIDATION_STATUS_ERROR,
                        "self_validation_error_contained",
                    ),
                ),
                detected_risks=("self_validation_error",),
                inconsistencies=("self_validation_error_contained",),
                audit_package={},
                reasons=["self_validation_error_contained"],
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _execution_reasons(
        self,
        request: SelfValidationRequest,
        runtime_active: bool,
        validation_permitted: bool,
        logs: list[dict[str, Any]],
    ) -> list[str]:
        reasons: list[str] = []
        if not validation_permitted:
            reasons.append("self_validation_not_permitted")
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not request.execution_id:
            reasons.append("missing_execution_id")
        if not request.outputs and not request.provider_responses:
            reasons.append("missing_execution_outputs")
        if request.expected_outputs and not request.outputs:
            reasons.append("expected_outputs_missing")
        logs.append(
            self._log(
                VALIDATION_TYPE_EXECUTION,
                VALIDATION_STATUS_INVALID if reasons else VALIDATION_STATUS_VALID,
                "execution reviewed",
                {"output_count": len(request.outputs)},
            )
        )
        return reasons

    def _file_reasons(
        self,
        request: SelfValidationRequest,
        logs: list[dict[str, Any]],
    ) -> tuple[list[str], list[str]]:
        reasons: list[str] = []
        risks: list[str] = []
        seen: set[str] = set()
        for path in request.modified_files:
            if not isinstance(path, str) or not path.strip():
                reasons.append("invalid_modified_file")
                continue
            normalized = path.replace("\\", "/")
            if normalized in seen:
                reasons.append("duplicate_modified_file")
            seen.add(normalized)
            if self._has(normalized.lower(), RUNTIME_CORE_HINTS):
                risks.append("runtime_core_file_modified")
                reasons.append("dangerous_file_change_detected")
        if not request.modified_files:
            risks.append("no_modified_files_declared")
        logs.append(
            self._log(
                VALIDATION_TYPE_FILE,
                VALIDATION_STATUS_INVALID if reasons else VALIDATION_STATUS_VALID,
                "modified files reviewed",
                {"modified_files": list(request.modified_files)},
            )
        )
        return self._unique(reasons), self._unique(risks)

    def _runtime_reasons(
        self,
        request: SelfValidationRequest,
        logs: list[dict[str, Any]],
    ) -> tuple[list[str], list[str]]:
        reasons: list[str] = []
        warnings: list[str] = []
        runtime = dict(request.runtime_state or {})
        lifecycle = dict(request.lifecycle_state or {})
        runtime_status = str(runtime.get("status") or runtime.get("state") or "")
        loop_state = str(runtime.get("loop_state") or runtime.get("loop") or "")
        if runtime_status.lower() in {"offline", "error", "failed"}:
            reasons.append("runtime_state_invalid")
        if loop_state.lower() in {"offline", "error", "failed"}:
            reasons.append("runtime_loop_invalid")
        if runtime_status.lower() == "degraded" or loop_state.lower() == "degraded":
            warnings.append("runtime_degraded")
        if lifecycle.get("state_transition_allowed") is False:
            reasons.append("state_transition_invalid")
        if lifecycle.get("lifecycle_transition_allowed") is False:
            reasons.append("lifecycle_transition_invalid")
        logs.append(
            self._log(
                VALIDATION_TYPE_RUNTIME,
                VALIDATION_STATUS_INVALID if reasons else VALIDATION_STATUS_VALID,
                "runtime consistency reviewed",
                {"runtime": runtime, "lifecycle": lifecycle},
            )
        )
        return self._unique(reasons), self._unique(warnings)

    def _risk_reasons(
        self,
        request: SelfValidationRequest,
        logs: list[dict[str, Any]],
    ) -> tuple[list[str], list[str]]:
        reasons: list[str] = []
        warnings: list[str] = []
        for note in request.risk_notes:
            text = str(note).lower()
            if self._has(text, SEVERE_RISK_HINTS):
                reasons.append("severe_risk_detected")
            else:
                warnings.append("risk_note_detected")
        if request.critical_change:
            warnings.append("critical_change_requires_external_audit")
        logs.append(
            self._log(
                VALIDATION_TYPE_RISK,
                VALIDATION_STATUS_INVALID if reasons else VALIDATION_STATUS_VALID,
                "risks reviewed",
                {"risk_notes": list(request.risk_notes)},
            )
        )
        return self._unique(reasons), self._unique(warnings)

    def _response_reasons(
        self,
        request: SelfValidationRequest,
        logs: list[dict[str, Any]],
    ) -> tuple[list[str], list[str]]:
        reasons: list[str] = []
        warnings: list[str] = []
        for response in request.provider_responses:
            data = self._as_dict(response)
            status = data.get("status")
            success = data.get("success")
            response_status = data.get("response_status")
            if success is False or status in {"rejected", "error", "failed"}:
                reasons.append("provider_response_invalid")
            if response_status == "rejected":
                reasons.append("provider_response_rejected")
            if data.get("audit_status") == "blocked":
                reasons.append("response_audit_blocked")
            response_reasons = data.get("reasons") or []
            if response_reasons and not reasons:
                warnings.append("provider_response_has_reasons")
        logs.append(
            self._log(
                VALIDATION_TYPE_RESPONSE,
                VALIDATION_STATUS_INVALID if reasons else VALIDATION_STATUS_VALID,
                "provider responses reviewed",
                {"response_count": len(request.provider_responses)},
            )
        )
        return self._unique(reasons), self._unique(warnings)

    def _validation_status(
        self,
        invalid: list[str],
        warnings: list[str],
    ) -> str:
        if invalid:
            return VALIDATION_STATUS_INVALID
        if warnings:
            return VALIDATION_STATUS_WARNING
        return VALIDATION_STATUS_VALID

    def _risk_status(self, invalid: list[str], risks: list[str]) -> str:
        if invalid:
            return RISK_STATUS_CRITICAL
        if risks:
            return RISK_STATUS_ELEVATED
        return RISK_STATUS_CLEAR

    def _audit_package(
        self,
        validation_id: str,
        request: SelfValidationRequest,
        validation_status: str,
        risk_status: str,
        validation_logs: list[dict[str, Any]],
        detected_risks: list[str],
        inconsistencies: list[str],
        warnings: list[str],
    ) -> dict[str, Any]:
        return {
            "validation_id": validation_id,
            "execution_id": request.execution_id,
            "task_id": request.task_id,
            "validation_status": validation_status,
            "risk_status": risk_status,
            "self_approved": False,
            "audit_required": True,
            "modified_files": list(request.modified_files),
            "output_count": len(request.outputs),
            "response_count": len(request.provider_responses),
            "validation_logs": [dict(log) for log in validation_logs],
            "detected_risks": list(detected_risks),
            "inconsistencies": list(inconsistencies),
            "warnings": list(warnings),
            "runtime_state": dict(request.runtime_state or {}),
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "metadata": dict(request.metadata),
        }

    def _result(
        self,
        status: str,
        success: bool,
        validation_id: str,
        request: SelfValidationRequest,
        validation_status: str,
        risk_status: str,
        audit_required: bool,
        continuation_blocked: bool,
        validation_logs: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        detected_risks: list[str] | tuple[str, ...],
        inconsistencies: list[str] | tuple[str, ...],
        audit_package: dict[str, Any],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> SelfValidationResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return SelfValidationResult(
            status=status,
            success=success,
            validation_id=validation_id,
            execution_id=request.execution_id,
            task_id=request.task_id,
            validation_status=validation_status,
            risk_status=risk_status,
            audit_required=audit_required,
            self_approved=False,
            continuation_blocked=continuation_blocked,
            runtime_protected=True,
            modified_files=tuple(request.modified_files),
            validation_logs=tuple(dict(log) for log in validation_logs),
            detected_risks=tuple(detected_risks),
            inconsistencies=tuple(inconsistencies),
            audit_package=dict(audit_package),
            output_count=len(request.outputs),
            response_count=len(request.provider_responses),
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _log(
        self,
        validation_type: str,
        status: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "validation_type": validation_type,
            "status": status,
            "message": message,
            "details": dict(details or {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _has(self, text: str, needles: tuple[str, ...]) -> bool:
        return any(needle in text for needle in needles)

    def _unique(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                unique.append(value)
        return unique

    def _publish(self, result: SelfValidationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_self_validation_result",
        ):
            self.status.mark_self_validation_result(result.to_dict())

    def _log_result(self, result: SelfValidationResult) -> None:
        if result.status == VALIDATION_STATUS_VALID:
            logger.info(
                "self_validation: valid validation_id=%s execution_id=%s",
                result.validation_id,
                result.execution_id,
            )
            return
        if result.status == VALIDATION_STATUS_INVALID:
            logger.warning(
                "self_validation: invalid validation_id=%s reasons=%s",
                result.validation_id,
                ",".join(result.reasons),
            )
            return
        if result.status == VALIDATION_STATUS_ERROR:
            logger.error(
                "self_validation: error validation_id=%s error=%s",
                result.validation_id,
                result.error,
            )
            return
        logger.info(
            "self_validation: warning validation_id=%s reasons=%s",
            result.validation_id,
            ",".join(result.reasons),
        )
