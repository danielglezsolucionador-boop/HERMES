"""
Vulcan scope enforcement for controlled Hermes backend execution.

This layer validates authorized file targets and operational boundaries before
code modification. It does not modify files, run workflows, or alter runtime.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.vulcan_prompt_protocol import VulcanPromptResult

logger = logging.getLogger(__name__)

SCOPE_STATUS_ENFORCED = "enforced"
SCOPE_STATUS_BLOCKED = "blocked"
SCOPE_STATUS_ERROR = "error"

DEFAULT_PROTECTED_SYSTEMS = (
    "governance",
    "security",
    "audit",
    "runtime_core",
    "operational_continuity",
)

PROTECTED_FILE_HINTS = {
    "governance": ("governance_", "approval_", "ecosystem_registry"),
    "security": ("security", "safety", "centinela"),
    "audit": ("audit_", "sentinel"),
    "runtime_core": ("runtime_loop.py", "task_runner.py", "polling"),
}

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
class VulcanScopeRequest:
    execution_id: str | None = None
    technical_scope: str | None = None
    authorized_files: tuple[str, ...] = field(default_factory=tuple)
    proposed_files: tuple[str, ...] = field(default_factory=tuple)
    modified_files: tuple[str, ...] = field(default_factory=tuple)
    protected_systems: tuple[str, ...] = field(default_factory=tuple)
    execution_limits: dict[str, Any] = field(default_factory=dict)
    architecture_boundaries: dict[str, Any] = field(default_factory=dict)
    governance_restrictions: tuple[str, ...] = field(default_factory=tuple)
    blocking_conditions: tuple[str, ...] = field(default_factory=tuple)
    prompt_protocol: VulcanPromptResult | dict[str, Any] | Any | None = None
    architecture_status: str | None = None
    runtime_status: str | None = None
    governance_status: str | None = None
    audit_status: str | None = None
    security_status: str | None = None
    scope_expansion_requested: bool = False
    unauthorized_file_modification_requested: bool = False
    architecture_override_requested: bool = False
    critical_protection_override_requested: bool = False
    full_system_refactor_requested: bool = False
    invent_execution_targets_requested: bool = False
    conceal_modified_files_requested: bool = False
    minimize_runtime_risks_requested: bool = False
    falsify_scope_requested: bool = False
    ignore_inconsistency_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VulcanScopeResult:
    status: str
    success: bool
    enforcement_id: str
    execution_id: str | None
    technical_scope: str | None
    authorized_files: tuple[str, ...]
    proposed_files: tuple[str, ...]
    modified_files: tuple[str, ...]
    protected_systems: tuple[str, ...]
    execution_limits: dict[str, Any]
    architecture_boundaries: dict[str, Any]
    governance_restrictions: tuple[str, ...]
    blocking_conditions: tuple[str, ...]
    scope_compliant: bool
    files_authorized: bool
    protected_systems_preserved: bool
    execution_limits_preserved: bool
    architecture_boundaries_preserved: bool
    governance_restrictions_respected: bool
    runtime_stability_preserved: bool
    operational_continuity_preserved: bool
    execution_consistency_preserved: bool
    reporting_honest: bool
    controlled_modification_ready: bool
    execution_authorized: bool
    report_payload: dict[str, Any] = field(default_factory=dict)
    enforcement_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "enforcement_id": self.enforcement_id,
            "execution_id": self.execution_id,
            "technical_scope": self.technical_scope,
            "authorized_files": list(self.authorized_files),
            "proposed_files": list(self.proposed_files),
            "modified_files": list(self.modified_files),
            "protected_systems": list(self.protected_systems),
            "execution_limits": dict(self.execution_limits),
            "architecture_boundaries": dict(self.architecture_boundaries),
            "governance_restrictions": list(self.governance_restrictions),
            "blocking_conditions": list(self.blocking_conditions),
            "scope_compliant": self.scope_compliant,
            "files_authorized": self.files_authorized,
            "protected_systems_preserved": self.protected_systems_preserved,
            "execution_limits_preserved": self.execution_limits_preserved,
            "architecture_boundaries_preserved": (
                self.architecture_boundaries_preserved
            ),
            "governance_restrictions_respected": (
                self.governance_restrictions_respected
            ),
            "runtime_stability_preserved": self.runtime_stability_preserved,
            "operational_continuity_preserved": (
                self.operational_continuity_preserved
            ),
            "execution_consistency_preserved": (
                self.execution_consistency_preserved
            ),
            "reporting_honest": self.reporting_honest,
            "controlled_modification_ready": self.controlled_modification_ready,
            "execution_authorized": self.execution_authorized,
            "report_payload": dict(self.report_payload),
            "enforcement_lifecycle": [
                dict(entry) for entry in self.enforcement_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class VulcanScopeEnforcement:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def enforce(
        self,
        request: VulcanScopeRequest,
        enforcement_permitted: bool = True,
    ) -> VulcanScopeResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        enforcement_id = str(uuid4())

        try:
            prompt_protocol = self._prompt_protocol(request.prompt_protocol)
            authorized_files = tuple(self._paths(request.authorized_files))
            proposed_files = tuple(
                self._proposed_files(request, prompt_protocol)
            )
            modified_files = tuple(self._paths(request.modified_files))
            protected_systems = tuple(
                self._protected_systems(request.protected_systems)
            )
            execution_limits = dict(request.execution_limits or {})
            architecture_boundaries = dict(request.architecture_boundaries or {})
            governance_restrictions = tuple(
                self._values(request.governance_restrictions)
            )
            blocking_conditions = tuple(
                self._blocking_conditions(request.blocking_conditions)
            )
            reasons = self._validation_reasons(
                request=request,
                prompt_protocol=prompt_protocol,
                authorized_files=authorized_files,
                proposed_files=proposed_files,
                modified_files=modified_files,
                protected_systems=protected_systems,
                execution_limits=execution_limits,
                architecture_boundaries=architecture_boundaries,
                enforcement_permitted=enforcement_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    SCOPE_STATUS_BLOCKED
                    if blocked
                    else SCOPE_STATUS_ENFORCED
                ),
                success=not blocked,
                enforcement_id=enforcement_id,
                request=request,
                prompt_protocol=prompt_protocol,
                authorized_files=authorized_files,
                proposed_files=proposed_files,
                modified_files=modified_files,
                protected_systems=protected_systems,
                execution_limits=execution_limits,
                architecture_boundaries=architecture_boundaries,
                governance_restrictions=governance_restrictions,
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
                enforcement_id=enforcement_id,
                request=request,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def validate(
        self,
        request: VulcanScopeRequest,
        enforcement_permitted: bool = True,
    ) -> VulcanScopeResult:
        return self.enforce(
            request,
            enforcement_permitted=enforcement_permitted,
        )

    def _result(
        self,
        status: str,
        success: bool,
        enforcement_id: str,
        request: VulcanScopeRequest,
        prompt_protocol: dict[str, Any],
        authorized_files: tuple[str, ...],
        proposed_files: tuple[str, ...],
        modified_files: tuple[str, ...],
        protected_systems: tuple[str, ...],
        execution_limits: dict[str, Any],
        architecture_boundaries: dict[str, Any],
        governance_restrictions: tuple[str, ...],
        blocking_conditions: tuple[str, ...],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> VulcanScopeResult:
        finished_at = datetime.now(timezone.utc)
        files_authorized = not self._unauthorized_files(
            proposed_files,
            authorized_files,
        ) and not self._unauthorized_files(modified_files, authorized_files)
        protected_preserved = not (
            request.critical_protection_override_requested
            or self._protected_boundary_violated(
                proposed_files,
                protected_systems,
                architecture_boundaries,
            )
        )
        limits_preserved = not self._execution_limits_violated(
            proposed_files,
            modified_files,
            execution_limits,
        )
        architecture_preserved = not (
            request.architecture_override_requested
            or self._architecture_unsafe(request.architecture_status)
        )
        governance_respected = not (
            self._normalize(request.governance_status)
            in BLOCKING_GOVERNANCE_STATUSES
            or self._normalize(request.security_status)
            in BLOCKING_GOVERNANCE_STATUSES
            or self._normalize(request.audit_status)
            in BLOCKING_GOVERNANCE_STATUSES
        )
        runtime_preserved = (
            self._normalize(request.runtime_status) not in UNSAFE_RUNTIME_STATUSES
        )
        consistency_preserved = not (
            request.scope_expansion_requested
            or request.full_system_refactor_requested
            or request.invent_execution_targets_requested
            or request.ignore_inconsistency_requested
        )
        reporting_honest = not (
            request.conceal_modified_files_requested
            or request.minimize_runtime_risks_requested
            or request.falsify_scope_requested
        )
        return VulcanScopeResult(
            status=status,
            success=success,
            enforcement_id=enforcement_id,
            execution_id=request.execution_id,
            technical_scope=request.technical_scope
            or prompt_protocol.get("technical_scope"),
            authorized_files=authorized_files,
            proposed_files=proposed_files,
            modified_files=modified_files,
            protected_systems=protected_systems,
            execution_limits=execution_limits,
            architecture_boundaries=architecture_boundaries,
            governance_restrictions=governance_restrictions,
            blocking_conditions=blocking_conditions,
            scope_compliant=success,
            files_authorized=files_authorized,
            protected_systems_preserved=protected_preserved,
            execution_limits_preserved=limits_preserved,
            architecture_boundaries_preserved=architecture_preserved,
            governance_restrictions_respected=governance_respected,
            runtime_stability_preserved=runtime_preserved,
            operational_continuity_preserved=protected_preserved
            and runtime_preserved,
            execution_consistency_preserved=consistency_preserved,
            reporting_honest=reporting_honest,
            controlled_modification_ready=success,
            execution_authorized=success,
            report_payload=self._report_payload(
                enforcement_id=enforcement_id,
                request=request,
                prompt_protocol=prompt_protocol,
                authorized_files=authorized_files,
                proposed_files=proposed_files,
                modified_files=modified_files,
                protected_systems=protected_systems,
                execution_limits=execution_limits,
                architecture_boundaries=architecture_boundaries,
                reasons=reasons,
            ),
            enforcement_lifecycle=(
                self._lifecycle("scope_identification"),
                self._lifecycle("execution_validation"),
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
        request: VulcanScopeRequest,
        prompt_protocol: dict[str, Any],
        authorized_files: tuple[str, ...],
        proposed_files: tuple[str, ...],
        modified_files: tuple[str, ...],
        protected_systems: tuple[str, ...],
        execution_limits: dict[str, Any],
        architecture_boundaries: dict[str, Any],
        enforcement_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not enforcement_permitted:
            reasons.append("vulcan_scope_enforcement_not_permitted")
        if prompt_protocol and prompt_protocol.get("status") != "interpreted":
            reasons.append("vulcan_prompt_protocol_not_interpreted")
        if not authorized_files:
            reasons.append("authorized_files_required")
        if not proposed_files and not modified_files:
            reasons.append("execution_file_targets_required")
        if self._unauthorized_files(proposed_files, authorized_files):
            reasons.append("proposed_files_outside_authorized_scope")
        if self._unauthorized_files(modified_files, authorized_files):
            reasons.append("modified_files_outside_authorized_scope")
        if self._paths_escape_scope((*proposed_files, *modified_files)):
            reasons.append("file_targets_escape_backend_scope")
        if self._protected_boundary_violated(
            proposed_files,
            protected_systems,
            architecture_boundaries,
        ):
            reasons.append("protected_system_boundary_violation")
        if self._execution_limits_violated(
            proposed_files,
            modified_files,
            execution_limits,
        ):
            reasons.append("execution_limits_exceeded")
        if request.scope_expansion_requested:
            reasons.append("scope_expansion_blocked")
        if request.unauthorized_file_modification_requested:
            reasons.append("unauthorized_file_modification_blocked")
        if request.architecture_override_requested:
            reasons.append("architecture_override_blocked")
        if request.critical_protection_override_requested:
            reasons.append("critical_protection_override_blocked")
        if request.full_system_refactor_requested:
            reasons.append("full_system_refactor_blocked")
        if request.invent_execution_targets_requested:
            reasons.append("invented_execution_targets_blocked")
        if (
            request.conceal_modified_files_requested
            or request.minimize_runtime_risks_requested
            or request.falsify_scope_requested
        ):
            reasons.append("dishonest_scope_reporting_blocked")
        if request.ignore_inconsistency_requested:
            reasons.append("backend_inconsistency_must_be_reported")
        if self._architecture_unsafe(request.architecture_status):
            reasons.append("architecture_status_unsafe")
        if self._normalize(request.runtime_status) in UNSAFE_RUNTIME_STATUSES:
            reasons.append("runtime_status_unsafe")
        if self._normalize(request.governance_status) in BLOCKING_GOVERNANCE_STATUSES:
            reasons.append("governance_status_blocked")
        if self._normalize(request.security_status) in BLOCKING_GOVERNANCE_STATUSES:
            reasons.append("security_status_blocked")
        if self._normalize(request.audit_status) in BLOCKING_GOVERNANCE_STATUSES:
            reasons.append("audit_status_blocked")
        return self._unique(reasons)

    def _prompt_protocol(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, VulcanPromptResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

    def _proposed_files(
        self,
        request: VulcanScopeRequest,
        prompt_protocol: dict[str, Any],
    ) -> list[str]:
        prompt_files = [
            str(path)
            for path in (prompt_protocol.get("file_targets") or [])
            if str(path).strip()
        ]
        return self._unique(
            [
                *self._paths(request.proposed_files),
                *self._paths(tuple(prompt_files)),
            ]
        )

    def _paths(self, values: tuple[str, ...]) -> list[str]:
        return self._unique(
            [
                str(value).strip().replace("\\", "/")
                for value in values
                if str(value).strip()
            ]
        )

    def _values(self, values: tuple[str, ...]) -> list[str]:
        return self._unique(
            [str(value).strip() for value in values if str(value).strip()]
        )

    def _protected_systems(self, values: tuple[str, ...]) -> list[str]:
        systems = [self._normalize(value) or "" for value in values]
        return self._unique(systems or list(DEFAULT_PROTECTED_SYSTEMS))

    def _blocking_conditions(self, values: tuple[str, ...]) -> list[str]:
        blocks = [str(value).strip() for value in values if str(value).strip()]
        return self._unique(
            blocks
            or [
                "scope_expansion",
                "unauthorized_file_target",
                "protected_system_override",
                "failed_required_validation",
            ]
        )

    def _unauthorized_files(
        self,
        files: tuple[str, ...],
        authorized_files: tuple[str, ...],
    ) -> list[str]:
        if not files or not authorized_files:
            return []
        return [
            path
            for path in files
            if not any(self._target_matches(path, allowed) for allowed in authorized_files)
        ]

    def _target_matches(self, target: str, allowed: str) -> bool:
        prefix = allowed.rstrip("*")
        if allowed.endswith("/") or allowed.endswith("*"):
            return target.startswith(prefix)
        return target == allowed

    def _paths_escape_scope(self, files: tuple[str, ...]) -> bool:
        return any(
            path.startswith("/")
            or ":" in path
            or ".." in path.split("/")
            for path in files
        )

    def _protected_boundary_violated(
        self,
        files: tuple[str, ...],
        protected_systems: tuple[str, ...],
        architecture_boundaries: dict[str, Any],
    ) -> bool:
        if architecture_boundaries.get("allow_protected_system_changes") is True:
            return False
        if not files:
            return False
        protected_hits = self._protected_file_hits(files, protected_systems)
        if not protected_hits:
            return False
        if architecture_boundaries.get("allow_runtime_core") is False:
            return "runtime_core" in protected_hits
        if architecture_boundaries.get("allow_governance_changes") is False:
            return bool(
                {"governance", "security", "audit"}.intersection(protected_hits)
            )
        return False

    def _protected_file_hits(
        self,
        files: tuple[str, ...],
        protected_systems: tuple[str, ...],
    ) -> set[str]:
        hits: set[str] = set()
        for path in files:
            lowered = path.lower()
            for system in protected_systems:
                hints = PROTECTED_FILE_HINTS.get(system, ())
                if any(hint in lowered for hint in hints):
                    hits.add(system)
        return hits

    def _execution_limits_violated(
        self,
        proposed_files: tuple[str, ...],
        modified_files: tuple[str, ...],
        execution_limits: dict[str, Any],
    ) -> bool:
        max_files = execution_limits.get("max_files")
        max_modified_files = execution_limits.get("max_modified_files")
        if max_files is not None and len(proposed_files) > int(max_files):
            return True
        if (
            max_modified_files is not None
            and len(modified_files) > int(max_modified_files)
        ):
            return True
        return False

    def _architecture_unsafe(self, value: Any) -> bool:
        return self._normalize(value) in {
            "broken",
            "corrupt",
            "inconsistent",
            "unsafe",
        }

    def _report_payload(
        self,
        enforcement_id: str,
        request: VulcanScopeRequest,
        prompt_protocol: dict[str, Any],
        authorized_files: tuple[str, ...],
        proposed_files: tuple[str, ...],
        modified_files: tuple[str, ...],
        protected_systems: tuple[str, ...],
        execution_limits: dict[str, Any],
        architecture_boundaries: dict[str, Any],
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "enforcement_id": enforcement_id,
            "execution_id": request.execution_id,
            "prompt_protocol_id": prompt_protocol.get("protocol_id"),
            "technical_scope": request.technical_scope
            or prompt_protocol.get("technical_scope"),
            "authorized_files": list(authorized_files),
            "proposed_files": list(proposed_files),
            "modified_files": list(modified_files),
            "protected_systems": list(protected_systems),
            "execution_limits": dict(execution_limits),
            "architecture_boundaries": dict(architecture_boundaries),
            "governance_restrictions": list(request.governance_restrictions),
            "blocking_conditions": list(request.blocking_conditions),
            "blocked_reasons": list(reasons),
        }

    def _error_result(
        self,
        enforcement_id: str,
        request: VulcanScopeRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> VulcanScopeResult:
        finished_at = datetime.now(timezone.utc)
        return VulcanScopeResult(
            status=SCOPE_STATUS_ERROR,
            success=False,
            enforcement_id=enforcement_id,
            execution_id=request.execution_id,
            technical_scope=request.technical_scope,
            authorized_files=tuple(self._paths(request.authorized_files)),
            proposed_files=tuple(self._paths(request.proposed_files)),
            modified_files=tuple(self._paths(request.modified_files)),
            protected_systems=tuple(
                self._protected_systems(request.protected_systems)
            ),
            execution_limits=dict(request.execution_limits or {}),
            architecture_boundaries=dict(request.architecture_boundaries or {}),
            governance_restrictions=tuple(
                self._values(request.governance_restrictions)
            ),
            blocking_conditions=tuple(
                self._blocking_conditions(request.blocking_conditions)
            ),
            scope_compliant=False,
            files_authorized=False,
            protected_systems_preserved=False,
            execution_limits_preserved=False,
            architecture_boundaries_preserved=False,
            governance_restrictions_respected=False,
            runtime_stability_preserved=False,
            operational_continuity_preserved=False,
            execution_consistency_preserved=False,
            reporting_honest=False,
            controlled_modification_ready=False,
            execution_authorized=False,
            report_payload={
                "enforcement_id": enforcement_id,
                "blocked_reasons": ["vulcan_scope_enforcement_error_contained"],
            },
            enforcement_lifecycle=(self._lifecycle(SCOPE_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("vulcan_scope_enforcement_error_contained",),
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

    def _publish(self, result: VulcanScopeResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_vulcan_scope_enforcement_result",
        ):
            self.status.mark_vulcan_scope_enforcement_result(result.to_dict())

    def _log_result(self, result: VulcanScopeResult) -> None:
        if result.status == SCOPE_STATUS_ERROR:
            logger.error(
                "vulcan_scope_enforcement: error enforcement_id=%s error=%s",
                result.enforcement_id,
                result.error,
            )
            return
        if result.status == SCOPE_STATUS_BLOCKED:
            logger.warning(
                "vulcan_scope_enforcement: blocked enforcement_id=%s reasons=%s",
                result.enforcement_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "vulcan_scope_enforcement: enforced enforcement_id=%s scope=%s",
            result.enforcement_id,
            result.technical_scope,
        )
