"""
Vulcan prompt protocol for controlled Hermes backend execution.

This layer interprets technical prompts into a constrained execution envelope.
It does not execute workflows, mutate runtime state, or change architecture.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

VULCAN_STATUS_INTERPRETED = "interpreted"
VULCAN_STATUS_BLOCKED = "blocked"
VULCAN_STATUS_ERROR = "error"

SUPPORTED_TECHNICAL_SCOPES = {
    "api",
    "backend",
    "database",
    "documentation",
    "governance_control",
    "operations",
    "provider",
    "runtime_observability",
    "tests",
}

REQUIRED_VALIDATIONS = (
    "pytest",
    "python -m py_compile",
    'python -c "import main"',
)

BLOCKING_GOVERNANCE_STATUSES = {
    "blocked",
    "critical_blocked",
    "critical_blocking",
    "halted",
    "quarantine",
    "rejected",
}

UNSAFE_RUNTIME_STATUSES = {
    "corrupt",
    "critical",
    "degraded_critical",
    "unsafe",
}


@dataclass(frozen=True)
class VulcanPromptRequest:
    prompt: str = ""
    execution_objective: str | None = None
    technical_scope: str | None = None
    file_targets: tuple[str, ...] = field(default_factory=tuple)
    allowed_file_targets: tuple[str, ...] = field(default_factory=tuple)
    validation_requirements: tuple[str, ...] = field(default_factory=tuple)
    risk_conditions: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    governance_status: str | None = None
    runtime_status: str | None = None
    architecture_context: dict[str, Any] = field(default_factory=dict)
    architecture_override_requested: bool = False
    governance_runtime_modification_requested: bool = False
    runtime_core_modification_requested: bool = False
    scope_expansion_requested: bool = False
    workflow_invention_requested: bool = False
    validation_bypass_requested: bool = False
    conceal_risks_requested: bool = False
    falsify_validations_requested: bool = False
    ignore_backend_inconsistency_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VulcanPromptResult:
    status: str
    success: bool
    protocol_id: str
    execution_objective: str | None
    technical_scope: str | None
    file_targets: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    risk_conditions: tuple[str, ...]
    blocking_conditions: tuple[str, ...]
    prompt_interpreted: bool
    technical_objective_identified: bool
    scope_valid: bool
    file_targets_valid: bool
    validations_identified: bool
    risks_identified: bool
    blocking_conditions_identified: bool
    architecture_integrity_preserved: bool
    runtime_stability_preserved: bool
    governance_consistency_preserved: bool
    technical_coherence_preserved: bool
    controlled_execution_ready: bool
    execution_authorized: bool
    handoff_required: bool
    report_payload: dict[str, Any] = field(default_factory=dict)
    protocol_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "protocol_id": self.protocol_id,
            "execution_objective": self.execution_objective,
            "technical_scope": self.technical_scope,
            "file_targets": list(self.file_targets),
            "validation_requirements": list(self.validation_requirements),
            "risk_conditions": list(self.risk_conditions),
            "blocking_conditions": list(self.blocking_conditions),
            "prompt_interpreted": self.prompt_interpreted,
            "technical_objective_identified": (
                self.technical_objective_identified
            ),
            "scope_valid": self.scope_valid,
            "file_targets_valid": self.file_targets_valid,
            "validations_identified": self.validations_identified,
            "risks_identified": self.risks_identified,
            "blocking_conditions_identified": (
                self.blocking_conditions_identified
            ),
            "architecture_integrity_preserved": (
                self.architecture_integrity_preserved
            ),
            "runtime_stability_preserved": self.runtime_stability_preserved,
            "governance_consistency_preserved": (
                self.governance_consistency_preserved
            ),
            "technical_coherence_preserved": (
                self.technical_coherence_preserved
            ),
            "controlled_execution_ready": self.controlled_execution_ready,
            "execution_authorized": self.execution_authorized,
            "handoff_required": self.handoff_required,
            "report_payload": dict(self.report_payload),
            "protocol_lifecycle": [
                dict(entry) for entry in self.protocol_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class VulcanPromptProtocol:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def interpret(
        self,
        request: VulcanPromptRequest,
        protocol_permitted: bool = True,
    ) -> VulcanPromptResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        protocol_id = str(uuid4())

        try:
            objective = self._objective(request)
            scope = self._scope(request)
            file_targets = tuple(self._file_targets(request.file_targets))
            validations = tuple(self._validations(request.validation_requirements))
            risks = tuple(self._risk_conditions(request.risk_conditions))
            blocking_conditions = tuple(
                self._blocking_conditions(request.blocking_conditions)
            )
            reasons = self._validation_reasons(
                request=request,
                objective=objective,
                scope=scope,
                file_targets=file_targets,
                validations=validations,
                protocol_permitted=protocol_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    VULCAN_STATUS_BLOCKED
                    if blocked
                    else VULCAN_STATUS_INTERPRETED
                ),
                success=not blocked,
                protocol_id=protocol_id,
                request=request,
                objective=objective,
                scope=scope,
                file_targets=file_targets,
                validations=validations,
                risks=risks,
                blocking_conditions=blocking_conditions,
                reasons=reasons,
                error=";".join(reasons) if blocked else None,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                protocol_id=protocol_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def assess(
        self,
        request: VulcanPromptRequest,
        protocol_permitted: bool = True,
    ) -> VulcanPromptResult:
        return self.interpret(
            request,
            protocol_permitted=protocol_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        protocol_id: str,
        request: VulcanPromptRequest,
        objective: str | None,
        scope: str | None,
        file_targets: tuple[str, ...],
        validations: tuple[str, ...],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> VulcanPromptResult:
        finished_at = datetime.now(timezone.utc)
        scope_valid = scope in SUPPORTED_TECHNICAL_SCOPES
        file_targets_valid = bool(file_targets) and not self._unauthorized_targets(
            file_targets,
            request.allowed_file_targets,
        )
        architecture_preserved = not (
            request.architecture_override_requested
            or self._architecture_inconsistent(request.architecture_context)
        )
        runtime_preserved = not (
            request.runtime_core_modification_requested
            or self._normalize(request.runtime_status) in UNSAFE_RUNTIME_STATUSES
        )
        governance_preserved = not (
            request.governance_runtime_modification_requested
            or self._normalize(request.governance_status)
            in BLOCKING_GOVERNANCE_STATUSES
        )
        technical_coherence_preserved = not (
            request.ignore_backend_inconsistency_requested
            or request.workflow_invention_requested
            or request.scope_expansion_requested
        )
        return VulcanPromptResult(
            status=status,
            success=success,
            protocol_id=protocol_id,
            execution_objective=objective,
            technical_scope=scope,
            file_targets=file_targets,
            validation_requirements=validations,
            risk_conditions=risks,
            blocking_conditions=blocking_conditions,
            prompt_interpreted=bool(objective and scope),
            technical_objective_identified=bool(objective),
            scope_valid=scope_valid,
            file_targets_valid=file_targets_valid,
            validations_identified=all(
                required in validations for required in REQUIRED_VALIDATIONS
            ),
            risks_identified=bool(risks),
            blocking_conditions_identified=bool(blocking_conditions),
            architecture_integrity_preserved=architecture_preserved,
            runtime_stability_preserved=runtime_preserved,
            governance_consistency_preserved=governance_preserved,
            technical_coherence_preserved=technical_coherence_preserved,
            controlled_execution_ready=success,
            execution_authorized=success,
            handoff_required=True,
            report_payload=self._report_payload(
                protocol_id=protocol_id,
                request=request,
                objective=objective,
                scope=scope,
                file_targets=file_targets,
                validations=validations,
                risks=risks,
                blocking_conditions=blocking_conditions,
                reasons=reasons,
            ),
            protocol_lifecycle=(
                self._lifecycle("prompt_interpretation"),
                self._lifecycle("technical_validation"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _validation_reasons(
        self,
        request: VulcanPromptRequest,
        objective: str | None,
        scope: str | None,
        file_targets: tuple[str, ...],
        validations: tuple[str, ...],
        protocol_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not protocol_permitted:
            reasons.append("vulcan_protocol_not_permitted")
        if not objective:
            reasons.append("execution_objective_required")
        if scope not in SUPPORTED_TECHNICAL_SCOPES:
            reasons.append("unsupported_technical_scope")
        if not file_targets:
            reasons.append("file_targets_required")
        if self._unauthorized_targets(file_targets, request.allowed_file_targets):
            reasons.append("unauthorized_file_targets")
        if self._file_targets_escape_scope(file_targets):
            reasons.append("file_targets_outside_backend_scope")
        if not all(required in validations for required in REQUIRED_VALIDATIONS):
            reasons.append("required_validations_missing")
        if request.architecture_override_requested:
            reasons.append("architecture_override_blocked")
        if request.governance_runtime_modification_requested:
            reasons.append("governance_runtime_modification_blocked")
        if request.runtime_core_modification_requested:
            reasons.append("runtime_core_modification_blocked")
        if request.scope_expansion_requested:
            reasons.append("scope_expansion_blocked")
        if request.workflow_invention_requested:
            reasons.append("workflow_invention_blocked")
        if request.validation_bypass_requested:
            reasons.append("validation_bypass_blocked")
        if request.conceal_risks_requested or request.falsify_validations_requested:
            reasons.append("dishonest_technical_reporting_blocked")
        if request.ignore_backend_inconsistency_requested:
            reasons.append("backend_inconsistency_must_be_reported")
        if self._normalize(request.governance_status) in BLOCKING_GOVERNANCE_STATUSES:
            reasons.append("governance_status_blocked")
        if self._normalize(request.runtime_status) in UNSAFE_RUNTIME_STATUSES:
            reasons.append("runtime_status_unsafe")
        if self._architecture_inconsistent(request.architecture_context):
            reasons.append("architecture_context_inconsistent")
        return self._unique(reasons)

    def _objective(self, request: VulcanPromptRequest) -> str | None:
        if request.execution_objective:
            return request.execution_objective.strip()
        prompt = request.prompt.strip()
        if not prompt:
            return None
        for raw_line in prompt.splitlines():
            line = raw_line.strip(" -\t")
            if not line or line.startswith("#"):
                continue
            lower = line.lower()
            if lower.startswith(("objective:", "objetivo:", "purpose:", "proposito:")):
                value = line.split(":", 1)[1].strip()
                return value or None
            if len(line) > 3:
                return line
        return None

    def _scope(self, request: VulcanPromptRequest) -> str:
        if request.technical_scope:
            return self._normalize(request.technical_scope) or ""
        prompt = request.prompt.lower()
        if any(word in prompt for word in ("runtime/status", "observability", "logs")):
            return "runtime_observability"
        if any(word in prompt for word in ("database", "postgres", "sql", "db")):
            return "database"
        if any(word in prompt for word in ("endpoint", "api", "/runtime")):
            return "api"
        if any(word in prompt for word in ("provider", "openrouter", "ai")):
            return "provider"
        if any(word in prompt for word in ("pytest", "test", "validacion")):
            return "tests"
        if any(word in prompt for word in ("governance", "approval", "audit")):
            return "governance_control"
        return "backend"

    def _file_targets(self, values: tuple[str, ...]) -> list[str]:
        return self._unique(
            [
                str(value).strip().replace("\\", "/")
                for value in values
                if str(value).strip()
            ]
        )

    def _validations(self, values: tuple[str, ...]) -> list[str]:
        return self._unique(
            [
                *[str(value).strip() for value in values if str(value).strip()],
                *REQUIRED_VALIDATIONS,
            ]
        )

    def _risk_conditions(self, values: tuple[str, ...]) -> list[str]:
        risks = [str(value).strip() for value in values if str(value).strip()]
        return self._unique(risks or ["no_known_risks_declared"])

    def _blocking_conditions(self, values: tuple[str, ...]) -> list[str]:
        blocks = [str(value).strip() for value in values if str(value).strip()]
        return self._unique(
            blocks
            or [
                "architecture_override",
                "runtime_core_modification",
                "failed_required_validation",
            ]
        )

    def _unauthorized_targets(
        self,
        file_targets: tuple[str, ...],
        allowed_file_targets: tuple[str, ...],
    ) -> list[str]:
        allowed = self._file_targets(allowed_file_targets)
        if not allowed:
            return []
        return [
            target
            for target in file_targets
            if not any(self._target_matches(target, item) for item in allowed)
        ]

    def _target_matches(self, target: str, allowed: str) -> bool:
        prefix = allowed.rstrip("*")
        if allowed.endswith("/") or allowed.endswith("*"):
            return target.startswith(prefix)
        return target == allowed

    def _file_targets_escape_scope(self, file_targets: tuple[str, ...]) -> bool:
        return any(
            target.startswith("/")
            or ":" in target
            or ".." in target.split("/")
            for target in file_targets
        )

    def _architecture_inconsistent(self, context: dict[str, Any]) -> bool:
        stability = self._normalize(context.get("architecture_stability"))
        compatibility = context.get("backend_compatibility")
        return stability in {"broken", "inconsistent", "unknown_critical"} or (
            compatibility is False
        )

    def _report_payload(
        self,
        protocol_id: str,
        request: VulcanPromptRequest,
        objective: str | None,
        scope: str | None,
        file_targets: tuple[str, ...],
        validations: tuple[str, ...],
        risks: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "protocol_id": protocol_id,
            "execution_objective": objective,
            "technical_scope": scope,
            "file_targets": list(file_targets),
            "allowed_file_targets": list(request.allowed_file_targets),
            "validation_requirements": list(validations),
            "risk_conditions": list(risks),
            "blocking_conditions": list(blocking_conditions),
            "governance_status": self._normalize(request.governance_status),
            "runtime_status": self._normalize(request.runtime_status),
            "blocked_reasons": list(reasons),
        }

    def _error_result(
        self,
        protocol_id: str,
        request: VulcanPromptRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> VulcanPromptResult:
        finished_at = datetime.now(timezone.utc)
        return VulcanPromptResult(
            status=VULCAN_STATUS_ERROR,
            success=False,
            protocol_id=protocol_id,
            execution_objective=request.execution_objective,
            technical_scope=self._normalize(request.technical_scope),
            file_targets=tuple(self._file_targets(request.file_targets)),
            validation_requirements=tuple(
                self._validations(request.validation_requirements)
            ),
            risk_conditions=tuple(self._risk_conditions(request.risk_conditions)),
            blocking_conditions=tuple(
                self._blocking_conditions(request.blocking_conditions)
            ),
            prompt_interpreted=False,
            technical_objective_identified=False,
            scope_valid=False,
            file_targets_valid=False,
            validations_identified=False,
            risks_identified=False,
            blocking_conditions_identified=False,
            architecture_integrity_preserved=False,
            runtime_stability_preserved=False,
            governance_consistency_preserved=False,
            technical_coherence_preserved=False,
            controlled_execution_ready=False,
            execution_authorized=False,
            handoff_required=True,
            report_payload={
                "protocol_id": protocol_id,
                "blocked_reasons": ["vulcan_prompt_protocol_error_contained"],
            },
            protocol_lifecycle=(self._lifecycle(VULCAN_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("vulcan_prompt_protocol_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

    def _normalize(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

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

    def _publish(self, result: VulcanPromptResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_vulcan_prompt_protocol_result",
        ):
            self.status.mark_vulcan_prompt_protocol_result(result.to_dict())

    def _log_result(self, result: VulcanPromptResult) -> None:
        if result.status == VULCAN_STATUS_ERROR:
            logger.error(
                "vulcan_prompt_protocol: error protocol_id=%s error=%s",
                result.protocol_id,
                result.error,
            )
            return
        if result.status == VULCAN_STATUS_BLOCKED:
            logger.warning(
                "vulcan_prompt_protocol: blocked protocol_id=%s reasons=%s",
                result.protocol_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "vulcan_prompt_protocol: interpreted protocol_id=%s scope=%s",
            result.protocol_id,
            result.technical_scope,
        )
