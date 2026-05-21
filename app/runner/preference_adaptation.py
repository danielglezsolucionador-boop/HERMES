"""
Controlled preference adaptation for Hermes runtime.

This layer detects operational preferences from human interactions and exposes
safe adaptation signals. It does not change governance, strategic objectives,
runtime architecture, or human authority.
"""
from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

PREFERENCE_TYPE_REPORTING = "reporting"
PREFERENCE_TYPE_WORKFLOW = "workflow"
PREFERENCE_TYPE_GOVERNANCE = "governance"
PREFERENCE_TYPE_EXECUTION = "execution"
PREFERENCE_TYPE_COMMUNICATION = "communication"
SUPPORTED_PREFERENCE_TYPES = {
    PREFERENCE_TYPE_REPORTING,
    PREFERENCE_TYPE_WORKFLOW,
    PREFERENCE_TYPE_GOVERNANCE,
    PREFERENCE_TYPE_EXECUTION,
    PREFERENCE_TYPE_COMMUNICATION,
}

ADAPTATION_STATUS_ADAPTED = "adapted"
ADAPTATION_STATUS_NO_PREFERENCES = "no_preferences"
ADAPTATION_STATUS_BLOCKED = "blocked"
ADAPTATION_STATUS_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
    "governance_approved",
}
VALIDATED_STATUSES = {"validated", "approved", "safe", "approved_with_warnings"}
SAFE_RUNTIME_STATES = {"active", "online", "ready", "stable"}


@dataclass(frozen=True)
class PreferenceAdaptationRequest:
    adaptation_id: str | None = None
    preference_type: str = PREFERENCE_TYPE_COMMUNICATION
    human_context: dict[str, Any] = field(default_factory=dict)
    interaction_history: tuple[Any, ...] = field(default_factory=tuple)
    decision_history: tuple[Any, ...] = field(default_factory=tuple)
    approval_history: tuple[Any, ...] = field(default_factory=tuple)
    rejection_history: tuple[Any, ...] = field(default_factory=tuple)
    reporting_feedback: tuple[Any, ...] = field(default_factory=tuple)
    workflow_preferences: tuple[Any, ...] = field(default_factory=tuple)
    workflow_learning: tuple[Any, ...] = field(default_factory=tuple)
    operational_memory: tuple[Any, ...] = field(default_factory=tuple)
    governance_status: str | None = None
    validation_status: str | None = None
    runtime_state: dict[str, Any] = field(default_factory=dict)
    application_requested: bool = False
    allow_governance_change: bool = False
    assume_strategic_authority: bool = False
    manipulation_requested: bool = False
    psychological_profile_requested: bool = False
    detected_risks: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PreferenceAdaptationResult:
    status: str
    success: bool
    adaptation_id: str
    preference_type: str | None
    human_context: dict[str, Any]
    adaptation_status: str
    governance_status: str | None
    validation_status: str | None
    application_status: str
    governance_compliant: bool
    operational_safe: bool
    validation_consistent: bool
    human_authority_preserved: bool
    context_safe: bool
    transparency_preserved: bool
    objectives_preserved: bool
    manipulation_blocked: bool
    dependency_risk_controlled: bool
    preferences_detected: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    reporting_adjustments: tuple[str, ...] = field(default_factory=tuple)
    workflow_adjustments: tuple[str, ...] = field(default_factory=tuple)
    governance_preferences: tuple[str, ...] = field(default_factory=tuple)
    execution_preferences: tuple[str, ...] = field(default_factory=tuple)
    communication_adjustments: tuple[str, ...] = field(default_factory=tuple)
    interaction_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    decision_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    approval_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    rejection_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    adaptation_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "adaptation_id": self.adaptation_id,
            "preference_type": self.preference_type,
            "human_context": dict(self.human_context),
            "adaptation_status": self.adaptation_status,
            "governance_status": self.governance_status,
            "validation_status": self.validation_status,
            "application_status": self.application_status,
            "governance_compliant": self.governance_compliant,
            "operational_safe": self.operational_safe,
            "validation_consistent": self.validation_consistent,
            "human_authority_preserved": self.human_authority_preserved,
            "context_safe": self.context_safe,
            "transparency_preserved": self.transparency_preserved,
            "objectives_preserved": self.objectives_preserved,
            "manipulation_blocked": self.manipulation_blocked,
            "dependency_risk_controlled": self.dependency_risk_controlled,
            "preferences_detected": [
                dict(preference) for preference in self.preferences_detected
            ],
            "reporting_adjustments": list(self.reporting_adjustments),
            "workflow_adjustments": list(self.workflow_adjustments),
            "governance_preferences": list(self.governance_preferences),
            "execution_preferences": list(self.execution_preferences),
            "communication_adjustments": list(self.communication_adjustments),
            "interaction_history": [
                dict(entry) for entry in self.interaction_history
            ],
            "decision_history": [dict(entry) for entry in self.decision_history],
            "approval_history": [dict(entry) for entry in self.approval_history],
            "rejection_history": [
                dict(entry) for entry in self.rejection_history
            ],
            "adaptation_lifecycle": [
                dict(entry) for entry in self.adaptation_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class PreferenceAdaptation:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def adapt(
        self,
        request: PreferenceAdaptationRequest,
        adaptation_permitted: bool = True,
        runtime_active: bool = True,
    ) -> PreferenceAdaptationResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        adaptation_id = request.adaptation_id or str(uuid4())

        try:
            preference_type = self._normalize(request.preference_type)
            history = self._interaction_history(request)
            checks = {
                "governance_compliant": self._governance_compliant(request),
                "operational_safe": (
                    runtime_active and self._runtime_safe(request)
                ),
                "validation_consistent": self._validation_consistent(request),
                "human_authority_preserved": (
                    not request.assume_strategic_authority
                ),
                "context_safe": self._context_safe(request),
                "objectives_preserved": not self._objective_change_requested(
                    request
                ),
            }
            reasons = self._validation_reasons(
                request=request,
                preference_type=preference_type,
                checks=checks,
                adaptation_permitted=adaptation_permitted,
            )
            if reasons:
                result = self._result(
                    status=ADAPTATION_STATUS_BLOCKED,
                    success=False,
                    adaptation_id=adaptation_id,
                    request=request,
                    preference_type=preference_type,
                    adaptation_status=ADAPTATION_STATUS_BLOCKED,
                    application_status="blocked",
                    checks=checks,
                    preferences=[],
                    history=history,
                    lifecycle=(
                        self._lifecycle("interaction_analysis_requested"),
                        self._lifecycle(ADAPTATION_STATUS_BLOCKED),
                    ),
                    reasons=reasons,
                    error=";".join(reasons),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            preferences = self._detect_preferences(preference_type, request, history)
            adapted = bool(preferences)
            result = self._result(
                status=(
                    ADAPTATION_STATUS_ADAPTED
                    if adapted
                    else ADAPTATION_STATUS_NO_PREFERENCES
                ),
                success=True,
                adaptation_id=adaptation_id,
                request=request,
                preference_type=preference_type,
                adaptation_status=(
                    "adaptation_validated"
                    if adapted
                    else ADAPTATION_STATUS_NO_PREFERENCES
                ),
                application_status=(
                    "applied"
                    if adapted and request.application_requested
                    else "suggested_only"
                    if adapted
                    else "not_available"
                ),
                checks=checks,
                preferences=preferences,
                history=history,
                lifecycle=(
                    self._lifecycle("interaction_analysis_requested"),
                    self._lifecycle("preference_detection_completed"),
                    self._lifecycle("adaptation_validated"),
                ),
                reasons=(
                    []
                    if not adapted or request.application_requested
                    else ["adaptation_application_requires_governance"]
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
                adaptation_id=adaptation_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def analyze(
        self,
        request: PreferenceAdaptationRequest,
        adaptation_permitted: bool = True,
        runtime_active: bool = True,
    ) -> PreferenceAdaptationResult:
        return self.adapt(
            request,
            adaptation_permitted=adaptation_permitted,
            runtime_active=runtime_active,
        )

    def _result(
        self,
        status: str,
        success: bool,
        adaptation_id: str,
        request: PreferenceAdaptationRequest,
        preference_type: str | None,
        adaptation_status: str,
        application_status: str,
        checks: dict[str, bool],
        preferences: list[dict[str, Any]],
        history: dict[str, tuple[dict[str, Any], ...]],
        lifecycle: tuple[dict[str, Any], ...],
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> PreferenceAdaptationResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return PreferenceAdaptationResult(
            status=status,
            success=success,
            adaptation_id=adaptation_id,
            preference_type=preference_type,
            human_context=dict(request.human_context),
            adaptation_status=adaptation_status,
            governance_status=self._normalize(request.governance_status),
            validation_status=self._normalize(request.validation_status),
            application_status=application_status,
            governance_compliant=checks["governance_compliant"],
            operational_safe=checks["operational_safe"],
            validation_consistent=checks["validation_consistent"],
            human_authority_preserved=checks["human_authority_preserved"],
            context_safe=checks["context_safe"],
            transparency_preserved=True,
            objectives_preserved=checks["objectives_preserved"],
            manipulation_blocked=True,
            dependency_risk_controlled=True,
            preferences_detected=tuple(preferences),
            reporting_adjustments=tuple(
                self._adjustments(preferences, PREFERENCE_TYPE_REPORTING)
            ),
            workflow_adjustments=tuple(
                self._adjustments(preferences, PREFERENCE_TYPE_WORKFLOW)
            ),
            governance_preferences=tuple(
                self._adjustments(preferences, PREFERENCE_TYPE_GOVERNANCE)
            ),
            execution_preferences=tuple(
                self._adjustments(preferences, PREFERENCE_TYPE_EXECUTION)
            ),
            communication_adjustments=tuple(
                self._adjustments(preferences, PREFERENCE_TYPE_COMMUNICATION)
            ),
            interaction_history=history["interaction_history"],
            decision_history=history["decision_history"],
            approval_history=history["approval_history"],
            rejection_history=history["rejection_history"],
            adaptation_lifecycle=lifecycle,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _detect_preferences(
        self,
        preference_type: str | None,
        request: PreferenceAdaptationRequest,
        history: dict[str, tuple[dict[str, Any], ...]],
    ) -> list[dict[str, Any]]:
        if preference_type not in SUPPORTED_PREFERENCE_TYPES:
            return []
        entries = [
            dict(request.human_context),
            *history["interaction_history"],
            *history["decision_history"],
            *history["approval_history"],
            *history["rejection_history"],
            *self._records(request.reporting_feedback),
            *self._records(request.workflow_preferences),
            *self._records(request.workflow_learning),
            *self._records(request.operational_memory),
        ]
        signals = Counter()
        for entry in entries:
            for key in self._preference_keys(preference_type):
                value = entry.get(key)
                if value:
                    signals[(key, str(value))] += 1
        return [
            self._preference(preference_type, key, value, count)
            for (key, value), count in signals.items()
        ]

    def _preference_keys(self, preference_type: str) -> tuple[str, ...]:
        mapping = {
            PREFERENCE_TYPE_REPORTING: (
                "detail_level",
                "report_format",
                "summary_format",
                "reporting_style",
            ),
            PREFERENCE_TYPE_WORKFLOW: (
                "workflow",
                "priority",
                "continuation_pace",
                "approval_pattern",
            ),
            PREFERENCE_TYPE_GOVERNANCE: (
                "risk_tolerance",
                "escalation_preference",
                "blocking_preference",
                "audit_expectation",
            ),
            PREFERENCE_TYPE_EXECUTION: (
                "execution_pacing",
                "provider_preference",
                "optimization_priority",
                "operational_style",
            ),
            PREFERENCE_TYPE_COMMUNICATION: (
                "tone",
                "clarity",
                "technical_level",
                "interaction_format",
            ),
        }
        return mapping.get(preference_type, ())

    def _preference(
        self,
        preference_type: str,
        key: str,
        value: str,
        count: int,
    ) -> dict[str, Any]:
        return {
            "preference_id": str(uuid4()),
            "preference_type": preference_type,
            "signal": key,
            "value": value,
            "count": count,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    def _adjustments(
        self,
        preferences: list[dict[str, Any]],
        preference_type: str,
    ) -> list[str]:
        adjustments: list[str] = []
        for preference in preferences:
            if preference.get("preference_type") != preference_type:
                continue
            signal = preference["signal"]
            value = preference["value"]
            if preference_type == PREFERENCE_TYPE_REPORTING:
                adjustments.append(f"align reporting {signal} to {value}")
            elif preference_type == PREFERENCE_TYPE_WORKFLOW:
                adjustments.append(f"respect workflow {signal} preference {value}")
            elif preference_type == PREFERENCE_TYPE_GOVERNANCE:
                adjustments.append(f"surface governance {signal} preference {value}")
            elif preference_type == PREFERENCE_TYPE_EXECUTION:
                adjustments.append(f"align execution {signal} to {value}")
            else:
                adjustments.append(f"align communication {signal} to {value}")
        return adjustments

    def _validation_reasons(
        self,
        request: PreferenceAdaptationRequest,
        preference_type: str | None,
        checks: dict[str, bool],
        adaptation_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not adaptation_permitted:
            reasons.append("preference_adaptation_not_permitted")
        if preference_type not in SUPPORTED_PREFERENCE_TYPES:
            reasons.append("unsupported_preference_type")
        if request.allow_governance_change:
            reasons.append("governance_change_blocked")
        if request.assume_strategic_authority:
            reasons.append("human_authority_override_blocked")
        if self._manipulation_requested(request):
            reasons.append("manipulation_blocked")
        if self._psychological_profile_requested(request):
            reasons.append("psychological_profile_blocked")
        if self._dependency_creation_requested(request):
            reasons.append("dependency_creation_blocked")
        if self._objective_change_requested(request):
            reasons.append("objective_modification_blocked")
        if request.application_requested and not checks["governance_compliant"]:
            reasons.append("governance_approval_required_for_application")
        if request.application_requested and not checks["validation_consistent"]:
            reasons.append("validated_adaptation_required")
        if request.application_requested and not checks["operational_safe"]:
            reasons.append("runtime_safety_required_for_application")
        return self._unique(reasons)

    def _governance_compliant(
        self,
        request: PreferenceAdaptationRequest,
    ) -> bool:
        if request.allow_governance_change:
            return False
        if request.application_requested:
            return (
                self._normalize(request.governance_status)
                in APPROVED_GOVERNANCE_STATUSES
            )
        return True

    def _validation_consistent(
        self,
        request: PreferenceAdaptationRequest,
    ) -> bool:
        if request.application_requested:
            return self._normalize(request.validation_status) in VALIDATED_STATUSES
        return True

    def _runtime_safe(self, request: PreferenceAdaptationRequest) -> bool:
        if not request.runtime_state:
            return not request.application_requested
        values = (
            request.runtime_state.get("state"),
            request.runtime_state.get("status"),
            request.runtime_state.get("loop_state"),
        )
        return any(self._normalize(value) in SAFE_RUNTIME_STATES for value in values)

    def _context_safe(self, request: PreferenceAdaptationRequest) -> bool:
        return not (
            self._psychological_profile_requested(request)
            or self._dependency_creation_requested(request)
        )

    def _interaction_history(
        self,
        request: PreferenceAdaptationRequest,
    ) -> dict[str, tuple[dict[str, Any], ...]]:
        return {
            "interaction_history": tuple(
                self._records(request.interaction_history)
            ),
            "decision_history": tuple(self._records(request.decision_history)),
            "approval_history": tuple(self._records(request.approval_history)),
            "rejection_history": tuple(self._records(request.rejection_history)),
        }

    def _records(self, values: tuple[Any, ...]) -> tuple[dict[str, Any], ...]:
        return tuple(self._as_dict(value) for value in values if value is not None)

    def _manipulation_requested(self, request: PreferenceAdaptationRequest) -> bool:
        if request.manipulation_requested:
            return True
        haystack = self._risk_text(request)
        return any(
            signal in haystack
            for signal in (
                "manipulate",
                "persuade_human_against_decision",
                "steer_human",
                "emotional_leverage",
            )
        )

    def _psychological_profile_requested(
        self,
        request: PreferenceAdaptationRequest,
    ) -> bool:
        if request.psychological_profile_requested:
            return True
        haystack = self._risk_text(request)
        return any(
            signal in haystack
            for signal in (
                "psychological_profile",
                "personality_profile",
                "emotional_profile",
                "mental_state",
            )
        )

    def _dependency_creation_requested(
        self,
        request: PreferenceAdaptationRequest,
    ) -> bool:
        haystack = self._risk_text(request)
        return any(
            signal in haystack
            for signal in (
                "create_dependency",
                "dependency_psychological",
                "make_human_depend",
                "emotional_dependence",
            )
        )

    def _objective_change_requested(
        self,
        request: PreferenceAdaptationRequest,
    ) -> bool:
        haystack = self._risk_text(request)
        return any(
            signal in haystack
            for signal in (
                "change_official_objective",
                "modify_objective",
                "replace_strategy",
                "assume_strategy",
            )
        )

    def _risk_text(self, request: PreferenceAdaptationRequest) -> str:
        values = [
            *request.detected_risks,
            *request.warnings,
            str(request.human_context),
            str(request.metadata),
        ]
        return " ".join(
            self._normalize(value) or "" for value in values if value
        )

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
        adaptation_id: str,
        request: PreferenceAdaptationRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> PreferenceAdaptationResult:
        return self._result(
            status=ADAPTATION_STATUS_ERROR,
            success=False,
            adaptation_id=adaptation_id,
            request=request,
            preference_type=self._normalize(request.preference_type),
            adaptation_status=ADAPTATION_STATUS_ERROR,
            application_status="blocked",
            checks={
                "governance_compliant": False,
                "operational_safe": False,
                "validation_consistent": False,
                "human_authority_preserved": False,
                "context_safe": False,
                "objectives_preserved": False,
            },
            preferences=[],
            history={
                "interaction_history": (),
                "decision_history": (),
                "approval_history": (),
                "rejection_history": (),
            },
            lifecycle=(self._lifecycle(ADAPTATION_STATUS_ERROR),),
            reasons=["preference_adaptation_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _publish(self, result: PreferenceAdaptationResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_preference_adaptation_result",
        ):
            self.status.mark_preference_adaptation_result(result.to_dict())

    def _log_result(self, result: PreferenceAdaptationResult) -> None:
        if result.status == ADAPTATION_STATUS_ERROR:
            logger.error(
                "preference_adaptation: error adaptation_id=%s error=%s",
                result.adaptation_id,
                result.error,
            )
            return
        if result.status == ADAPTATION_STATUS_BLOCKED:
            logger.warning(
                "preference_adaptation: blocked adaptation_id=%s reasons=%s",
                result.adaptation_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "preference_adaptation: %s adaptation_id=%s type=%s preferences=%s",
            result.status,
            result.adaptation_id,
            result.preference_type,
            len(result.preferences_detected),
        )
