from app.runner.governance_safety import GovernanceSafety, GovernanceSafetyRequest
from app.runner.operational_task_discovery import (
    OperationalTaskDiscovery,
    OperationalTaskDiscoveryRequest,
)
from app.services.runtime_status import RuntimeStatus


ROADMAP = (
    "5.7.4_GOVERNANCE_ESCALATION.md",
    "5.7.5_GOVERNANCE_SAFETY.md",
    "5.7.6_OPERATIONAL_TASK_DISCOVERY.md",
)


def test_operational_task_discovery_detects_official_sources_and_metrics():
    status = RuntimeStatus()
    discovery = OperationalTaskDiscovery(status=status)

    result = discovery.discover(
        OperationalTaskDiscoveryRequest(
            roadmap=ROADMAP,
            completed_workflows=("5.7.4_GOVERNANCE_ESCALATION.md",),
            operational_queue=(
                {
                    "task_id": "queue-1",
                    "title": "approved queue task",
                    "status": "approved",
                    "priority": "normal",
                },
            ),
            executive_messages=(
                {
                    "task_id": "ceo-1",
                    "instruction": "continue approved operational work",
                    "status": "requested",
                    "authority_source": "CEO",
                },
            ),
            governance_status="approved",
            approval_status="approved",
            execution_permission="authorized",
            runtime_status="online",
            execution_context={"phase": "5"},
        )
    )

    assert result.status == "tasks_discovered"
    assert result.success is True
    assert result.discovered_count == 4
    assert "5.7.5_GOVERNANCE_SAFETY.md" in result.pending_workflows
    assert result.execution_prepared is True
    assert result.unauthorized_execution_blocked is True
    assert result.roadmap_preserved is True

    metrics = status.operational_task_discovery_metrics()
    assert metrics["operational_task_discovery_status"] == "tasks_discovered"
    assert metrics["operational_tasks_discovered"] == 4
    assert metrics["execution_prepared"] is True


def test_operational_task_discovery_blocks_unauthorized_source_and_execution():
    discovery = OperationalTaskDiscovery()

    result = discovery.discover(
        OperationalTaskDiscoveryRequest(
            requested_sources=("roadmap_repository", "unofficial_source"),
            source_authorizations={"roadmap_repository": False},
            roadmap=ROADMAP,
            execution_context={"execution_id": "discovery-blocked"},
            execute_discovered_tasks_requested=True,
            modify_roadmap_requested=True,
            ignore_governance_requested=True,
            conceal_pending_tasks_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert "roadmap_repository_unauthorized" in result.reasons
    assert "unofficial_source_unsupported_source" in result.reasons
    assert "unauthorized_execution_blocked" in result.reasons
    assert "roadmap_modification_blocked" in result.reasons
    assert "governance_bypass_blocked" in result.reasons
    assert "honest_discovery_required" in result.reasons
    assert result.candidates == ()


def test_operational_task_discovery_respects_governance_safety_block():
    safety = GovernanceSafety().validate(
        GovernanceSafetyRequest(
            safety_type="security",
            execution_id="execution-governance-block",
            security_status="critical",
            runtime_status="online",
        )
    )
    discovery = OperationalTaskDiscovery()

    result = discovery.discover(
        OperationalTaskDiscoveryRequest(
            roadmap=ROADMAP,
            completed_workflows=("5.7.4_GOVERNANCE_ESCALATION.md",),
            governance_safety=safety,
            runtime_status="online",
        )
    )

    assert result.status == "blocked"
    assert "governance_safety_block_active" in result.reasons
    assert result.execution_prepared is False


def test_operational_task_discovery_filters_invalid_queue_and_executive_items():
    discovery = OperationalTaskDiscovery()

    result = discovery.discover(
        OperationalTaskDiscoveryRequest(
            requested_sources=("operational_queue", "executive_communication"),
            operational_queue=(
                {"task_id": "valid", "title": "valid task", "status": "pending"},
                {"task_id": "done", "title": "done task", "status": "done"},
                {"title": "missing id", "status": "pending"},
            ),
            executive_messages=(
                {
                    "task_id": "invalid-exec",
                    "instruction": "do work",
                    "status": "requested",
                    "authority_source": "UNKNOWN",
                },
            ),
            governance_status="approved",
            approval_status="approved",
            execution_permission="authorized",
            runtime_status="online",
        )
    )

    assert result.status == "tasks_discovered"
    assert result.discovered_count == 1
    assert result.ignored_reasons["non_pending_task"] == 1
    assert result.ignored_reasons["missing_task_identity"] == 1
    assert result.ignored_reasons["unauthorized_executive_source"] == 1


def test_operational_task_discovery_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    discovery = OperationalTaskDiscovery(status=status)

    def broken_sources(*args, **kwargs):
        raise RuntimeError("source discovery exploded")

    monkeypatch.setattr(discovery, "_sources", broken_sources)

    result = discovery.discover(OperationalTaskDiscoveryRequest())

    assert result.status == "error"
    assert result.success is False
    assert "operational_task_discovery_error_contained" in result.reasons
    metrics = status.operational_task_discovery_metrics()
    assert metrics["operational_task_discovery_errors"] == 1
