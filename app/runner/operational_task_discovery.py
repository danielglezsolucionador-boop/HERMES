"""
Operational task discovery for Hermes runtime.

This layer reviews official work sources and detects pending operational work.
It does not execute tasks, mutate roadmap files, create arbitrary workflows, or
override governance.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.governance_safety import GovernanceSafetyResult

logger = logging.getLogger(__name__)

SOURCE_ROADMAP = "roadmap_repository"
SOURCE_OPERATIONAL_QUEUE = "operational_queue"
SOURCE_GOVERNANCE = "governance_source"
SOURCE_EXECUTIVE = "executive_communication"
APPROVED_TASK_SOURCES = {
    SOURCE_ROADMAP,
    SOURCE_OPERATIONAL_QUEUE,
    SOURCE_GOVERNANCE,
    SOURCE_EXECUTIVE,
}

DISCOVERY_STATUS_DISCOVERED = "tasks_discovered"
DISCOVERY_STATUS_EMPTY = "empty"
DISCOVERY_STATUS_BLOCKED = "blocked"
DISCOVERY_STATUS_ERROR = "error"

APPROVED_STATUSES = {
    "approved",
    "authorized",
    "authorized_by_human",
    "human_approved",
    "validated",
}
AUTHORIZED_EXECUTION_STATUSES = {
    "authorized",
    "approved",
    "ready",
    "permitted",
    "validated",
}
PENDING_QUEUE_STATUSES = {
    "pending",
    "approved",
    "queued",
    "ready",
    "requested",
}
EXECUTIVE_AUTHORITIES = {"CEO", "CEREBRO"}
SAFE_RUNTIME_STATUSES = {"active", "online", "ready", "stable"}
BLOCKING_STATUSES = {
    "active",
    "blocked",
    "critical",
    "critical_blocking",
    "critical_blocked",
    "quarantine",
}


@dataclass(frozen=True)
class OperationalTaskCandidate:
    task_id: str
    task_source: str
    task_type: str
    title: str
    workflow: str | None = None
    execution_context: dict[str, Any] = field(default_factory=dict)
    governance_status: str | None = None
    approval_status: str | None = None
    execution_status: str | None = None
    priority: str | None = None
    reporting_authority: str | None = None
    blocking_status: str | None = None
    discovery_status: str = "detected"

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_source": self.task_source,
            "task_type": self.task_type,
            "title": self.title,
            "workflow": self.workflow,
            "execution_context": dict(self.execution_context),
            "governance_status": self.governance_status,
            "approval_status": self.approval_status,
            "execution_status": self.execution_status,
            "priority": self.priority,
            "reporting_authority": self.reporting_authority,
            "blocking_status": self.blocking_status,
            "discovery_status": self.discovery_status,
        }


@dataclass(frozen=True)
class OperationalTaskDiscoveryRequest:
    discovery_id: str | None = None
    requested_sources: tuple[str, ...] = field(default_factory=tuple)
    source_authorizations: dict[str, bool] = field(default_factory=dict)
    roadmap: tuple[str, ...] = field(default_factory=tuple)
    completed_workflows: tuple[str, ...] = field(default_factory=tuple)
    operational_queue: tuple[Any, ...] = field(default_factory=tuple)
    governance_items: tuple[Any, ...] = field(default_factory=tuple)
    executive_messages: tuple[Any, ...] = field(default_factory=tuple)
    execution_context: dict[str, Any] = field(default_factory=dict)
    governance_status: str | None = None
    approval_status: str | None = None
    execution_permission: str | None = None
    execution_status: str | None = None
    runtime_status: str | None = None
    blocking_status: str | None = None
    governance_safety: GovernanceSafetyResult | dict[str, Any] | Any | None = None
    create_arbitrary_workflow_requested: bool = False
    modify_roadmap_requested: bool = False
    execute_discovered_tasks_requested: bool = False
    ignore_governance_requested: bool = False
    overwrite_priorities_requested: bool = False
    conceal_pending_tasks_requested: bool = False
    falsify_execution_status_requested: bool = False
    minimize_blocking_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationalTaskDiscoveryResult:
    status: str
    success: bool
    discovery_id: str
    discovery_status: str
    discovered_count: int
    task_sources: tuple[str, ...]
    source_status: dict[str, str]
    candidates: tuple[OperationalTaskCandidate, ...] = field(default_factory=tuple)
    pending_workflows: tuple[str, ...] = field(default_factory=tuple)
    execution_requests: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    governance_instructions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    ignored_count: int = 0
    ignored_reasons: dict[str, int] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)
    governance_status: str | None = None
    approval_status: str | None = None
    execution_status: str | None = None
    runtime_status: str | None = None
    blocking_status: str | None = None
    execution_prepared: bool = False
    unauthorized_execution_blocked: bool = True
    roadmap_preserved: bool = True
    governance_preserved: bool = True
    audit_consistency_preserved: bool = True
    operational_safety_preserved: bool = True
    runtime_stability_preserved: bool = True
    execution_transparency_preserved: bool = True
    operational_continuity_preserved: bool = True
    traceability_preserved: bool = True
    report_payload: dict[str, Any] = field(default_factory=dict)
    discovery_lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
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
            "discovery_id": self.discovery_id,
            "discovery_status": self.discovery_status,
            "discovered_count": self.discovered_count,
            "task_sources": list(self.task_sources),
            "source_status": dict(self.source_status),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "pending_workflows": list(self.pending_workflows),
            "execution_requests": [
                dict(request) for request in self.execution_requests
            ],
            "governance_instructions": [
                dict(item) for item in self.governance_instructions
            ],
            "ignored_count": self.ignored_count,
            "ignored_reasons": dict(self.ignored_reasons),
            "execution_context": dict(self.execution_context),
            "governance_status": self.governance_status,
            "approval_status": self.approval_status,
            "execution_status": self.execution_status,
            "runtime_status": self.runtime_status,
            "blocking_status": self.blocking_status,
            "execution_prepared": self.execution_prepared,
            "unauthorized_execution_blocked": (
                self.unauthorized_execution_blocked
            ),
            "roadmap_preserved": self.roadmap_preserved,
            "governance_preserved": self.governance_preserved,
            "audit_consistency_preserved": self.audit_consistency_preserved,
            "operational_safety_preserved": self.operational_safety_preserved,
            "runtime_stability_preserved": self.runtime_stability_preserved,
            "execution_transparency_preserved": (
                self.execution_transparency_preserved
            ),
            "operational_continuity_preserved": (
                self.operational_continuity_preserved
            ),
            "traceability_preserved": self.traceability_preserved,
            "report_payload": dict(self.report_payload),
            "discovery_lifecycle": [
                dict(entry) for entry in self.discovery_lifecycle
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class OperationalTaskDiscovery:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def discover(
        self,
        request: OperationalTaskDiscoveryRequest,
        runtime_active: bool = True,
        discovery_permitted: bool = True,
    ) -> OperationalTaskDiscoveryResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        discovery_id = request.discovery_id or str(uuid4())

        try:
            governance_safety = self._as_dict(request.governance_safety)
            sources = self._sources(request)
            source_status = self._source_status(request, sources)
            candidates, ignored = self._candidates(
                request,
                sources,
                source_status,
            )
            statuses = self._statuses(request, governance_safety)
            reasons = self._validation_reasons(
                request=request,
                source_status=source_status,
                statuses=statuses,
                runtime_active=runtime_active,
                discovery_permitted=discovery_permitted,
            )
            blocked = bool(reasons)
            result = self._result(
                status=(
                    DISCOVERY_STATUS_BLOCKED
                    if blocked
                    else DISCOVERY_STATUS_DISCOVERED
                    if candidates
                    else DISCOVERY_STATUS_EMPTY
                ),
                success=not blocked,
                discovery_id=discovery_id,
                request=request,
                sources=sources,
                source_status=source_status,
                candidates=candidates,
                ignored=ignored,
                statuses=statuses,
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
                discovery_id=discovery_id,
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
        discovery_id: str,
        request: OperationalTaskDiscoveryRequest,
        sources: tuple[str, ...],
        source_status: dict[str, str],
        candidates: list[OperationalTaskCandidate],
        ignored: dict[str, int],
        statuses: dict[str, Any],
        reasons: list[str],
        error: str | None,
        started: float,
        started_at: datetime,
    ) -> OperationalTaskDiscoveryResult:
        finished_at = datetime.now(timezone.utc)
        pending_workflows = tuple(
            candidate.workflow
            for candidate in candidates
            if candidate.task_source == SOURCE_ROADMAP and candidate.workflow
        )
        execution_requests = tuple(
            candidate.to_dict()
            for candidate in candidates
            if candidate.task_type == "execution_request"
        )
        governance_instructions = tuple(
            candidate.to_dict()
            for candidate in candidates
            if candidate.task_source == SOURCE_GOVERNANCE
        )
        return OperationalTaskDiscoveryResult(
            status=status,
            success=success,
            discovery_id=discovery_id,
            discovery_status=status,
            discovered_count=len(candidates) if success else 0,
            task_sources=sources,
            source_status=dict(source_status),
            candidates=tuple(candidates) if success else tuple(),
            pending_workflows=pending_workflows if success else tuple(),
            execution_requests=execution_requests if success else tuple(),
            governance_instructions=(
                governance_instructions if success else tuple()
            ),
            ignored_count=sum(ignored.values()),
            ignored_reasons=dict(ignored),
            execution_context=dict(statuses["execution_context"]),
            governance_status=statuses["governance_status"],
            approval_status=statuses["approval_status"],
            execution_status=statuses["execution_status"],
            runtime_status=statuses["runtime_status"],
            blocking_status=statuses["blocking_status"],
            execution_prepared=success and bool(candidates),
            unauthorized_execution_blocked=not (
                request.execute_discovered_tasks_requested
            ),
            roadmap_preserved=not request.modify_roadmap_requested,
            governance_preserved=not request.ignore_governance_requested,
            audit_consistency_preserved=True,
            operational_safety_preserved=not (
                request.create_arbitrary_workflow_requested
                or request.overwrite_priorities_requested
            ),
            runtime_stability_preserved=statuses["runtime_stable"],
            execution_transparency_preserved=not (
                request.conceal_pending_tasks_requested
                or request.falsify_execution_status_requested
            ),
            operational_continuity_preserved=True,
            traceability_preserved=True,
            report_payload=self._report_payload(
                discovery_id=discovery_id,
                sources=sources,
                candidates=candidates if success else [],
                statuses=statuses,
                reasons=reasons,
            ),
            discovery_lifecycle=(
                self._lifecycle("source_validation_completed"),
                self._lifecycle("task_discovery_completed"),
                self._lifecycle(status),
            ),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=tuple(reasons),
            error=error,
            metadata=dict(request.metadata),
        )

    def _sources(
        self,
        request: OperationalTaskDiscoveryRequest,
    ) -> tuple[str, ...]:
        if request.requested_sources:
            return tuple(self._normalize(source) or "" for source in request.requested_sources)
        sources: list[str] = []
        if request.roadmap:
            sources.append(SOURCE_ROADMAP)
        if request.operational_queue:
            sources.append(SOURCE_OPERATIONAL_QUEUE)
        if request.governance_items:
            sources.append(SOURCE_GOVERNANCE)
        if request.executive_messages:
            sources.append(SOURCE_EXECUTIVE)
        return tuple(sources or (SOURCE_ROADMAP,))

    def _source_status(
        self,
        request: OperationalTaskDiscoveryRequest,
        sources: tuple[str, ...],
    ) -> dict[str, str]:
        status: dict[str, str] = {}
        for source in sources:
            if source not in APPROVED_TASK_SOURCES:
                status[source] = "unsupported_source"
                continue
            authorized = request.source_authorizations.get(source, True)
            status[source] = "authorized" if authorized else "unauthorized"
        return status

    def _candidates(
        self,
        request: OperationalTaskDiscoveryRequest,
        sources: tuple[str, ...],
        source_status: dict[str, str],
    ) -> tuple[list[OperationalTaskCandidate], dict[str, int]]:
        candidates: list[OperationalTaskCandidate] = []
        ignored: dict[str, int] = {}
        if self._source_allowed(SOURCE_ROADMAP, sources, source_status):
            candidates.extend(self._roadmap_candidates(request))
        if self._source_allowed(SOURCE_OPERATIONAL_QUEUE, sources, source_status):
            self._append_items(
                candidates,
                ignored,
                request.operational_queue,
                SOURCE_OPERATIONAL_QUEUE,
                default_type="queue_task",
            )
        if self._source_allowed(SOURCE_GOVERNANCE, sources, source_status):
            self._append_items(
                candidates,
                ignored,
                request.governance_items,
                SOURCE_GOVERNANCE,
                default_type="governance_instruction",
            )
        if self._source_allowed(SOURCE_EXECUTIVE, sources, source_status):
            self._append_items(
                candidates,
                ignored,
                request.executive_messages,
                SOURCE_EXECUTIVE,
                default_type="execution_request",
            )
        return candidates, ignored

    def _roadmap_candidates(
        self,
        request: OperationalTaskDiscoveryRequest,
    ) -> list[OperationalTaskCandidate]:
        completed = set(request.completed_workflows)
        pending = [workflow for workflow in request.roadmap if workflow not in completed]
        candidates: list[OperationalTaskCandidate] = []
        for workflow in pending:
            candidates.append(
                OperationalTaskCandidate(
                    task_id=f"roadmap:{workflow}",
                    task_source=SOURCE_ROADMAP,
                    task_type="workflow",
                    title=workflow,
                    workflow=workflow,
                    execution_context=dict(request.execution_context),
                    governance_status=self._normalize(request.governance_status),
                    approval_status=self._normalize(request.approval_status),
                    execution_status=self._normalize(request.execution_status)
                    or "pending",
                    priority="roadmap_order",
                    reporting_authority="CEREBRO",
                    blocking_status=self._normalize(request.blocking_status),
                )
            )
        return candidates

    def _append_items(
        self,
        candidates: list[OperationalTaskCandidate],
        ignored: dict[str, int],
        items: tuple[Any, ...],
        source: str,
        default_type: str,
    ) -> None:
        for item in items:
            record = self._as_dict(item)
            candidate, reason = self._candidate_from_record(
                record,
                source,
                default_type,
            )
            if reason:
                ignored[reason] = ignored.get(reason, 0) + 1
                continue
            assert candidate is not None
            candidates.append(candidate)

    def _candidate_from_record(
        self,
        record: dict[str, Any],
        source: str,
        default_type: str,
    ) -> tuple[OperationalTaskCandidate | None, str | None]:
        task_id = record.get("task_id") or record.get("id")
        title = record.get("title") or record.get("instruction") or record.get("workflow")
        if not task_id or not title:
            return None, "missing_task_identity"
        item_status = self._normalize(record.get("status") or record.get("task_status"))
        if item_status and item_status not in PENDING_QUEUE_STATUSES:
            return None, "non_pending_task"
        authority = record.get("authority_source") or record.get("decided_by")
        if source == SOURCE_EXECUTIVE and authority not in EXECUTIVE_AUTHORITIES:
            return None, "unauthorized_executive_source"
        return (
            OperationalTaskCandidate(
                task_id=str(task_id),
                task_source=source,
                task_type=str(record.get("task_type") or default_type),
                title=str(title),
                workflow=record.get("workflow"),
                execution_context=dict(record.get("execution_context") or {}),
                governance_status=self._normalize(record.get("governance_status")),
                approval_status=self._normalize(record.get("approval_status")),
                execution_status=item_status or "pending",
                priority=record.get("priority"),
                reporting_authority=authority or record.get("reporting_authority"),
                blocking_status=self._normalize(record.get("blocking_status")),
            ),
            None,
        )

    def _statuses(
        self,
        request: OperationalTaskDiscoveryRequest,
        governance_safety: dict[str, Any],
    ) -> dict[str, Any]:
        runtime_status = self._normalize(
            request.runtime_status or governance_safety.get("runtime_status")
        )
        return {
            "execution_context": dict(request.execution_context),
            "governance_status": self._normalize(
                request.governance_status
                or governance_safety.get("governance_status")
            ),
            "approval_status": self._normalize(
                request.approval_status or governance_safety.get("approval_status")
            ),
            "execution_permission": self._normalize(request.execution_permission),
            "execution_status": self._normalize(
                request.execution_status
                or governance_safety.get("execution_status")
            ),
            "runtime_status": runtime_status,
            "runtime_stable": runtime_status in {None, *SAFE_RUNTIME_STATUSES},
            "blocking_status": self._normalize(
                request.blocking_status
                or governance_safety.get("blocking_status")
            ),
            "governance_safety_status": self._normalize(
                governance_safety.get("status")
            ),
        }

    def _validation_reasons(
        self,
        request: OperationalTaskDiscoveryRequest,
        source_status: dict[str, str],
        statuses: dict[str, Any],
        runtime_active: bool,
        discovery_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not discovery_permitted:
            reasons.append("operational_task_discovery_not_permitted")
        for source, status in source_status.items():
            if status != "authorized":
                reasons.append(f"{source}_{status}")
        if statuses["governance_status"] not in {None, *APPROVED_STATUSES}:
            reasons.append("governance_approval_required")
        if statuses["approval_status"] not in {None, *APPROVED_STATUSES}:
            reasons.append("approval_required")
        if statuses["execution_permission"] not in {
            None,
            *AUTHORIZED_EXECUTION_STATUSES,
        }:
            reasons.append("execution_permission_required")
        if statuses["blocking_status"] in BLOCKING_STATUSES:
            reasons.append("blocking_condition_active")
        if not statuses["runtime_stable"]:
            reasons.append("runtime_stability_required")
        if statuses["governance_safety_status"] == "blocked":
            reasons.append("governance_safety_block_active")
        if request.create_arbitrary_workflow_requested:
            reasons.append("arbitrary_workflow_creation_blocked")
        if request.modify_roadmap_requested:
            reasons.append("roadmap_modification_blocked")
        if request.execute_discovered_tasks_requested:
            reasons.append("unauthorized_execution_blocked")
        if request.ignore_governance_requested:
            reasons.append("governance_bypass_blocked")
        if request.overwrite_priorities_requested:
            reasons.append("execution_priority_override_blocked")
        if (
            request.conceal_pending_tasks_requested
            or request.falsify_execution_status_requested
            or request.minimize_blocking_requested
        ):
            reasons.append("honest_discovery_required")
        return self._unique(reasons)

    def _source_allowed(
        self,
        source: str,
        sources: tuple[str, ...],
        source_status: dict[str, str],
    ) -> bool:
        return source in sources and source_status.get(source) == "authorized"

    def _report_payload(
        self,
        discovery_id: str,
        sources: tuple[str, ...],
        candidates: list[OperationalTaskCandidate],
        statuses: dict[str, Any],
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "discovery_id": discovery_id,
            "task_sources": list(sources),
            "discovered_count": len(candidates),
            "candidate_ids": [candidate.task_id for candidate in candidates],
            "pending_workflows": [
                candidate.workflow
                for candidate in candidates
                if candidate.task_source == SOURCE_ROADMAP and candidate.workflow
            ],
            "governance_status": statuses["governance_status"],
            "approval_status": statuses["approval_status"],
            "execution_status": statuses["execution_status"],
            "runtime_status": statuses["runtime_status"],
            "blocking_status": statuses["blocking_status"],
            "blocked_reasons": list(reasons),
        }

    def _as_dict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, GovernanceSafetyResult):
            return value.to_dict()
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            return result if isinstance(result, dict) else {}
        return {}

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

    def _error_result(
        self,
        discovery_id: str,
        request: OperationalTaskDiscoveryRequest,
        error: str,
        started: float,
        started_at: datetime,
    ) -> OperationalTaskDiscoveryResult:
        finished_at = datetime.now(timezone.utc)
        return OperationalTaskDiscoveryResult(
            status=DISCOVERY_STATUS_ERROR,
            success=False,
            discovery_id=discovery_id,
            discovery_status=DISCOVERY_STATUS_ERROR,
            discovered_count=0,
            task_sources=tuple(request.requested_sources),
            source_status={},
            execution_context=dict(request.execution_context),
            governance_status=self._normalize(request.governance_status),
            approval_status=self._normalize(request.approval_status),
            execution_status=self._normalize(request.execution_status),
            runtime_status=self._normalize(request.runtime_status),
            blocking_status=self._normalize(request.blocking_status),
            execution_prepared=False,
            discovery_lifecycle=(self._lifecycle(DISCOVERY_STATUS_ERROR),),
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((time.perf_counter() - started) * 1000),
            reasons=("operational_task_discovery_error_contained",),
            error=error,
            metadata=dict(request.metadata),
        )

    def _publish(self, result: OperationalTaskDiscoveryResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_operational_task_discovery_result",
        ):
            self.status.mark_operational_task_discovery_result(result.to_dict())

    def _log_result(self, result: OperationalTaskDiscoveryResult) -> None:
        if result.status == DISCOVERY_STATUS_ERROR:
            logger.error(
                "operational_task_discovery: error discovery_id=%s error=%s",
                result.discovery_id,
                result.error,
            )
            return
        if result.status == DISCOVERY_STATUS_BLOCKED:
            logger.warning(
                "operational_task_discovery: blocked discovery_id=%s reasons=%s",
                result.discovery_id,
                ",".join(result.reasons),
            )
            return
        logger.info(
            "operational_task_discovery: %s discovery_id=%s discovered=%s",
            result.status,
            result.discovery_id,
            result.discovered_count,
        )
