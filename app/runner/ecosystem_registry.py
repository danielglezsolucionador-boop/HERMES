"""
Official ecosystem registry for Hermes runtime.

This registry keeps the operational map of systems, authorities, roles, and
responsibility boundaries. It is static and controlled: Hermes can inspect and
validate authority relationships, but it cannot invent authorities or mutate the
ecosystem hierarchy without explicit governance.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

REGISTRY_STATUS_REGISTERED = "registered"
REGISTRY_STATUS_VALIDATED = "validated"
REGISTRY_STATUS_BLOCKED = "blocked"
REGISTRY_STATUS_ERROR = "error"

APPROVED_GOVERNANCE_STATUSES = {
    "approved",
    "human_approved",
    "authorized_by_human",
    "governance_approved",
}


@dataclass(frozen=True)
class EcosystemSystem:
    system_id: str
    system_type: str
    authority_level: str
    responsibility_scope: tuple[str, ...]
    governance_status: str = "approved"
    security_status: str = "clear"
    operational_status: str = "active"
    reports_to: str | None = None
    coordinates_with: tuple[str, ...] = field(default_factory=tuple)
    responsibilities: tuple[str, ...] = field(default_factory=tuple)
    boundaries: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_id": self.system_id,
            "system_type": self.system_type,
            "authority_level": self.authority_level,
            "responsibility_scope": list(self.responsibility_scope),
            "governance_status": self.governance_status,
            "security_status": self.security_status,
            "operational_status": self.operational_status,
            "reports_to": self.reports_to,
            "coordinates_with": list(self.coordinates_with),
            "responsibilities": list(self.responsibilities),
            "boundaries": list(self.boundaries),
        }


@dataclass(frozen=True)
class EcosystemRegistryRequest:
    system_id: str | None = None
    action: str = "inspect"
    target_system_id: str | None = None
    responsibility_scope: str | None = None
    requested_authority_level: str | None = None
    governance_status: str | None = None
    security_status: str | None = None
    operational_status: str | None = None
    future_system: EcosystemSystem | dict[str, Any] | None = None
    authority_override_requested: bool = False
    create_unregistered_system: bool = False
    alter_hierarchy_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EcosystemRegistryResult:
    status: str
    success: bool
    registry_id: str
    system_id: str | None
    action: str
    target_system_id: str | None
    system_type: str | None
    authority_level: str | None
    responsibility_scope: tuple[str, ...]
    governance_status: str | None
    security_status: str | None
    operational_status: str | None
    authority_respected: bool
    authority_conflict_detected: bool
    hierarchy_preserved: bool
    governance_preserved: bool
    security_escalation_respected: bool
    future_expansion_safe: bool
    official_systems: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    active_authorities: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    coordination_hierarchy: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    selected_system: dict[str, Any] = field(default_factory=dict)
    target_system: dict[str, Any] = field(default_factory=dict)
    registry_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "registry_id": self.registry_id,
            "system_id": self.system_id,
            "action": self.action,
            "target_system_id": self.target_system_id,
            "system_type": self.system_type,
            "authority_level": self.authority_level,
            "responsibility_scope": list(self.responsibility_scope),
            "governance_status": self.governance_status,
            "security_status": self.security_status,
            "operational_status": self.operational_status,
            "authority_respected": self.authority_respected,
            "authority_conflict_detected": self.authority_conflict_detected,
            "hierarchy_preserved": self.hierarchy_preserved,
            "governance_preserved": self.governance_preserved,
            "security_escalation_respected": self.security_escalation_respected,
            "future_expansion_safe": self.future_expansion_safe,
            "official_systems": [
                dict(system) for system in self.official_systems
            ],
            "active_authorities": [
                dict(authority) for authority in self.active_authorities
            ],
            "coordination_hierarchy": [
                dict(item) for item in self.coordination_hierarchy
            ],
            "selected_system": dict(self.selected_system),
            "target_system": dict(self.target_system),
            "registry_lifecycle": [
                dict(entry) for entry in self.registry_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class EcosystemRegistry:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status
        self._systems = self._official_systems()

    def snapshot(self) -> EcosystemRegistryResult:
        return self.validate(EcosystemRegistryRequest(action="inspect"))

    def validate(
        self,
        request: EcosystemRegistryRequest,
        registry_permitted: bool = True,
    ) -> EcosystemRegistryResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        try:
            system = self.get_system(request.system_id)
            target = self.get_system(request.target_system_id)
            reasons = self._validation_reasons(
                request=request,
                system=system,
                target=target,
                registry_permitted=registry_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    REGISTRY_STATUS_BLOCKED
                    if blocked
                    else REGISTRY_STATUS_REGISTERED
                    if request.action == "inspect"
                    else REGISTRY_STATUS_VALIDATED
                ),
                success=not blocked,
                request=request,
                system=system,
                target=target,
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
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def get_system(self, system_id: str | None) -> EcosystemSystem | None:
        if system_id is None:
            return None
        return self._systems.get(self._normalize(system_id))

    def register_future_system(
        self,
        system: EcosystemSystem,
        governance_status: str | None,
    ) -> EcosystemRegistryResult:
        return self.validate(
            EcosystemRegistryRequest(
                action="register_future_system",
                future_system=system,
                governance_status=governance_status,
            )
        )

    def _result(
        self,
        status: str,
        success: bool,
        request: EcosystemRegistryRequest,
        system: EcosystemSystem | None,
        target: EcosystemSystem | None,
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> EcosystemRegistryResult:
        finished_at = datetime.now(timezone.utc)
        selected = system.to_dict() if system else {}
        target_payload = target.to_dict() if target else {}
        return EcosystemRegistryResult(
            status=status,
            success=success,
            registry_id="ecosystem-registry",
            system_id=system.system_id if system else request.system_id,
            action=request.action,
            target_system_id=target.system_id if target else request.target_system_id,
            system_type=system.system_type if system else None,
            authority_level=system.authority_level if system else None,
            responsibility_scope=(
                system.responsibility_scope if system else tuple()
            ),
            governance_status=(
                system.governance_status
                if system
                else self._normalize(request.governance_status)
            ),
            security_status=(
                system.security_status
                if system
                else self._normalize(request.security_status)
            ),
            operational_status=(
                system.operational_status
                if system
                else self._normalize(request.operational_status)
            ),
            authority_respected=not self._authority_conflict(request, system),
            authority_conflict_detected=self._authority_conflict(
                request,
                system,
            ),
            hierarchy_preserved=not request.alter_hierarchy_requested,
            governance_preserved=not request.authority_override_requested,
            security_escalation_respected=not self._security_conflict(
                request,
                system,
            ),
            future_expansion_safe="future_system_not_authorized" not in reasons,
            official_systems=tuple(
                system.to_dict() for system in self._systems.values()
            ),
            active_authorities=tuple(self._active_authorities()),
            coordination_hierarchy=tuple(self._coordination_hierarchy()),
            selected_system=selected,
            target_system=target_payload,
            registry_lifecycle=(
                self._lifecycle("registry_loaded"),
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
        request: EcosystemRegistryRequest,
        system: EcosystemSystem | None,
        target: EcosystemSystem | None,
        registry_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not registry_permitted:
            reasons.append("ecosystem_registry_not_permitted")
        if request.system_id and system is None:
            reasons.append("unknown_system")
        if request.target_system_id and target is None:
            reasons.append("unknown_target_system")
        if request.authority_override_requested:
            reasons.append("authority_override_blocked")
        if request.alter_hierarchy_requested:
            reasons.append("hierarchy_alteration_blocked")
        if request.create_unregistered_system:
            reasons.append("unregistered_system_creation_blocked")
        if self._authority_conflict(request, system):
            reasons.append("authority_conflict_detected")
        if self._security_conflict(request, system):
            reasons.append("security_authority_required")
        if request.future_system and not self._future_system_allowed(request):
            reasons.append("future_system_not_authorized")
        return self._unique(reasons)

    def _authority_conflict(
        self,
        request: EcosystemRegistryRequest,
        system: EcosystemSystem | None,
    ) -> bool:
        if system is None:
            return False
        requested = self._normalize(request.requested_authority_level)
        if requested and requested != self._normalize(system.authority_level):
            return True
        scope = self._normalize(request.responsibility_scope)
        if scope and scope not in {
            self._normalize(item) for item in system.responsibility_scope
        }:
            return True
        if system.system_id == "HERMES" and request.action in {
            "redefine_strategy",
            "alter_governance",
            "override_authority",
        }:
            return True
        return False

    def _security_conflict(
        self,
        request: EcosystemRegistryRequest,
        system: EcosystemSystem | None,
    ) -> bool:
        action = self._normalize(request.action)
        if action in {"quarantine", "critical_block", "security_escalation"}:
            return system is None or system.system_id != "CENTINELA"
        return False

    def _future_system_allowed(self, request: EcosystemRegistryRequest) -> bool:
        return (
            self._normalize(request.governance_status)
            in APPROVED_GOVERNANCE_STATUSES
            and not request.authority_override_requested
            and not request.alter_hierarchy_requested
        )

    def _active_authorities(self) -> list[dict[str, Any]]:
        return [
            {
                "system_id": system.system_id,
                "authority_level": system.authority_level,
                "responsibility_scope": list(system.responsibility_scope),
            }
            for system in self._systems.values()
            if system.authority_level in {
                "strategic_final",
                "executive_coordination",
                "security_authority",
                "technical_audit",
                "backend_authority",
            }
        ]

    def _coordination_hierarchy(self) -> list[dict[str, Any]]:
        return [
            {
                "system_id": system.system_id,
                "reports_to": system.reports_to,
                "coordinates_with": list(system.coordinates_with),
            }
            for system in self._systems.values()
        ]

    def _official_systems(self) -> dict[str, EcosystemSystem]:
        systems = (
            EcosystemSystem(
                system_id="CEO",
                system_type="human_authority",
                authority_level="strategic_final",
                responsibility_scope=(
                    "strategic_vision",
                    "final_decisions",
                    "superior_governance",
                    "critical_approval",
                    "ecosystem_control",
                ),
                responsibilities=(
                    "vision estrategica",
                    "decisiones finales",
                    "governance superior",
                ),
            ),
            EcosystemSystem(
                system_id="CEREBRO",
                system_type="chief_of_staff",
                authority_level="executive_coordination",
                responsibility_scope=(
                    "executive_coordination",
                    "strategic_routing",
                    "operational_orchestration",
                    "ecosystem_supervision",
                    "business_continuity",
                    "report_consolidation",
                ),
                reports_to="CEO",
                coordinates_with=("HERMES", "FORJA", "SENTINEL", "CENTINELA"),
                boundaries=(
                    "does_not_replace_ceo",
                    "does_not_program_directly",
                    "does_not_replace_human_governance",
                ),
            ),
            EcosystemSystem(
                system_id="HERMES",
                system_type="technical_operations",
                authority_level="technical_runtime",
                responsibility_scope=(
                    "execution_runtime",
                    "automation_workflows",
                    "technical_maintenance",
                    "technical_orchestration",
                    "continuation_engine",
                    "execution_optimization",
                ),
                reports_to="CEREBRO",
                coordinates_with=("VULCAN", "SENTINEL", "CENTINELA"),
                boundaries=(
                    "does_not_redefine_business_strategy",
                    "does_not_replace_human_governance",
                    "does_not_alter_official_authorities",
                ),
            ),
            EcosystemSystem(
                system_id="FORJA",
                system_type="technology_factory",
                authority_level="technology_factory",
                responsibility_scope=(
                    "tools",
                    "systems",
                    "apis",
                    "platforms",
                    "reusable_structures",
                    "technology_expansion",
                ),
                reports_to="CEREBRO",
                coordinates_with=("HERMES", "VULCAN", "SENTINEL"),
                boundaries=(
                    "does_not_replace_governance",
                    "does_not_approve_architecture_alone",
                ),
            ),
            EcosystemSystem(
                system_id="VULCAN",
                system_type="backend_engineering",
                authority_level="backend_authority",
                responsibility_scope=(
                    "backend_implementation",
                    "apis",
                    "runtime_engineering",
                    "infrastructure_coding",
                    "backend_modifications",
                ),
                reports_to="HERMES",
                coordinates_with=("SENTINEL",),
            ),
            EcosystemSystem(
                system_id="SENTINEL",
                system_type="technical_auditor",
                authority_level="technical_audit",
                responsibility_scope=(
                    "technical_auditing",
                    "coherence_validation",
                    "handoff_validation",
                    "architecture_review",
                    "runtime_audit",
                ),
                reports_to="CEREBRO",
                coordinates_with=("HERMES", "VULCAN", "CENTINELA"),
                boundaries=(
                    "does_not_build_features",
                    "does_not_modify_main_code",
                    "does_not_replace_human_governance",
                ),
            ),
            EcosystemSystem(
                system_id="CENTINELA",
                system_type="security_authority",
                authority_level="security_authority",
                responsibility_scope=(
                    "cybersecurity_escalation",
                    "threat_detection",
                    "quarantine_authority",
                    "critical_blocking",
                    "security_governance",
                ),
                reports_to="CEO",
                coordinates_with=("CEREBRO", "HERMES", "SENTINEL"),
                responsibilities=(
                    "bloquear execution critica",
                    "detener workflows peligrosos",
                    "activar quarantine runtime",
                ),
            ),
        )
        return {self._normalize(system.system_id): system for system in systems}

    def _lifecycle(self, state: str) -> dict[str, Any]:
        return {
            "state": state,
            "at": datetime.now(timezone.utc).isoformat(),
        }

    def _normalize(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower().replace("-", "_").replace(" ", "_")

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
        request: EcosystemRegistryRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> EcosystemRegistryResult:
        finished_at = datetime.now(timezone.utc)
        return EcosystemRegistryResult(
            status=REGISTRY_STATUS_ERROR,
            success=False,
            registry_id="ecosystem-registry",
            system_id=request.system_id,
            action=request.action,
            target_system_id=request.target_system_id,
            system_type=None,
            authority_level=None,
            responsibility_scope=tuple(),
            governance_status=self._normalize(request.governance_status),
            security_status=self._normalize(request.security_status),
            operational_status=self._normalize(request.operational_status),
            authority_respected=False,
            authority_conflict_detected=True,
            hierarchy_preserved=False,
            governance_preserved=False,
            security_escalation_respected=False,
            future_expansion_safe=False,
            registry_lifecycle=(self._lifecycle(REGISTRY_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("ecosystem_registry_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

    def _publish(self, result: EcosystemRegistryResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_ecosystem_registry_result",
        ):
            self.status.mark_ecosystem_registry_result(result.to_dict())

    def _log_result(self, result: EcosystemRegistryResult) -> None:
        if result.status == REGISTRY_STATUS_ERROR:
            logger.error(
                "ecosystem_registry: error action=%s error=%s",
                result.action,
                result.error,
            )
            return
        if result.status == REGISTRY_STATUS_BLOCKED:
            logger.warning(
                "ecosystem_registry: blocked system=%s reasons=%s",
                result.system_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "ecosystem_registry: %s action=%s systems=%s",
            result.status,
            result.action,
            len(result.official_systems),
        )
