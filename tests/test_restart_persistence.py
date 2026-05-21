from app.runner.restart_persistence import (
    RestartPersistence,
    RestartPersistenceRequest,
)
from app.services.runtime_status import RuntimeStatus


def _persistence_request(**overrides):
    workflow_id = "10.3_RESTART_PERSISTENCE.md"
    values = {
        "restart_id": "restart-10-3",
        "workflow_id": workflow_id,
        "runtime_restart_detected": True,
        "execution_interruption_detected": True,
        "execution_state": {"execution_id": "execution-10-3"},
        "workflow_state": {"workflow_id": workflow_id, "step": "restart"},
        "restored_state": {"workflow_id": workflow_id, "step": "resumed"},
        "runtime_context": {"status": "online", "loop_state": "active"},
        "restart_status": "restored",
        "continuation_status": "recovery_validated",
        "governance_status": "approved",
        "recovery_status": "recovered",
        "execution_status": "resumed",
        "operational_status": "stable",
        "checkpoint_recovery": {
            "status": "recovery_prepared",
            "workflow_id": workflow_id,
            "restored_state": {"workflow_id": workflow_id},
            "execution_context": {"execution_id": "execution-10-3"},
        },
        "execution_resume": {
            "status": "resumed",
            "workflow_id": workflow_id,
            "continuation_status": "recovery_validated",
            "restored_state": {"workflow_id": workflow_id},
            "execution_context": {"execution_id": "execution-10-3"},
        },
        "failure_recovery": {
            "status": "recovered",
            "success": True,
            "workflow_id": workflow_id,
            "failure_detected": True,
        },
        "metadata": {"phase": "10.3"},
    }
    values.update(overrides)
    return RestartPersistenceRequest(**values)


def test_restart_persistence_restores_state_and_metrics():
    status = RuntimeStatus()
    persistence = RestartPersistence(status=status)

    result = persistence.restore(_persistence_request())

    assert result.status == "restored"
    assert result.success is True
    assert result.restart_detected is True
    assert result.persistence_valid is True
    assert result.continuation_allowed is True
    assert result.execution_state_restored is True

    metrics = status.restart_persistence_metrics()
    assert metrics["restart_persistence_status"] == "restored"
    assert metrics["restart_persistences_restored"] == 1
    assert metrics["restart_persistence_errors"] == 0
    assert metrics["persistence_valid"] is True


def test_restart_persistence_blocks_invalid_restoration():
    persistence = RestartPersistence()

    result = persistence.restore(
        _persistence_request(
            execution_state={},
            workflow_state={},
            restored_state={},
            checkpoint_recovery={},
            execution_resume={},
            runtime_context={"status": "degraded", "loop_state": "stalled"},
            restart_status="corrupt",
            continuation_status="broken",
            governance_status="pending",
            recovery_status="blocked",
            execution_status="blocked",
            restart_inconsistencies=("restart drift",),
            blocking_conditions=("manual restart review required",),
        )
    )

    assert result.status == "blocked"
    assert result.continuation_allowed is False
    assert "execution_state_required" in result.reasons
    assert "workflow_continuity_required" in result.reasons
    assert "runtime_context_required" in result.reasons
    assert "restart_status_required" in result.reasons
    assert "governance_alignment_required" in result.reasons
    assert "recovery_status_required" in result.reasons
    assert "execution_consistency_required" in result.reasons
    assert "operational_stability_required" in result.reasons
    assert "restart_blocking_conditions_active" in result.reasons


def test_restart_persistence_blocks_invalid_continuation_requests():
    persistence = RestartPersistence()

    result = persistence.restore(
        _persistence_request(
            blocking_conditions=("restart validation missing",),
            ignore_restart_inconsistencies_requested=True,
            overwrite_workflow_history_requested=True,
            alter_governance_state_requested=True,
            continue_corrupt_runtime_requested=True,
            restore_corrupt_runtime_requested=True,
            hide_restart_failures_requested=True,
            minimize_corruption_risks_requested=True,
            falsify_continuation_status_requested=True,
            ignore_blocking_conditions_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "restart_inconsistency_ignore_blocked" in result.reasons
    assert "workflow_history_overwrite_blocked" in result.reasons
    assert "governance_state_alteration_blocked" in result.reasons
    assert "corrupt_runtime_continuation_blocked" in result.reasons
    assert "corrupt_runtime_restoration_blocked" in result.reasons
    assert "restart_failure_concealment_blocked" in result.reasons
    assert "corruption_risk_minimization_blocked" in result.reasons
    assert "continuation_status_falsification_blocked" in result.reasons
    assert "blocking_condition_ignore_blocked" in result.reasons


def test_restart_persistence_blocks_failed_recovery_context():
    persistence = RestartPersistence()

    result = persistence.restore(
        _persistence_request(
            failure_recovery={
                "status": "blocked",
                "success": False,
                "workflow_id": "10.3_RESTART_PERSISTENCE.md",
                "failure_detected": True,
            }
        )
    )

    assert result.status == "blocked"
    assert "runtime_context_required" in result.reasons
    assert "failure_recovery_blocked" in result.restart_conditions
    assert "runtime_context_failed" in result.restart_conditions


def test_restart_persistence_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    persistence = RestartPersistence(status=status)

    def broken_checks(*args, **kwargs):
        raise RuntimeError("restart persistence exploded")

    monkeypatch.setattr(persistence, "_checks", broken_checks)

    result = persistence.restore(_persistence_request())

    assert result.status == "error"
    assert "restart_persistence_error_contained" in result.reasons

    metrics = status.restart_persistence_metrics()
    assert metrics["restart_persistence_status"] == "error"
    assert metrics["restart_persistence_errors"] == 1
