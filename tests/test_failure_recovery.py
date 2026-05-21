from app.runner.failure_recovery import (
    FailureRecovery,
    FailureRecoveryRequest,
)
from app.services.runtime_status import RuntimeStatus


def _recovery_request(**overrides):
    workflow_id = "10.2_FAILURE_RECOVERY.md"
    values = {
        "recovery_id": "failure-recovery-10-2",
        "workflow_id": workflow_id,
        "failure_type": "runtime_failure",
        "failure_detected": True,
        "runtime_failures": ("provider timeout",),
        "workflow_interruptions": ("execution interrupted",),
        "recovery_requirements": ("restore execution continuity",),
        "workflow_state": {"workflow_id": workflow_id, "step": "recovery"},
        "restored_state": {"workflow_id": workflow_id, "step": "resumed"},
        "runtime_state": {"status": "online", "loop_state": "active"},
        "runtime_status": "online",
        "recovery_status": "recovered",
        "continuation_status": "recovery_validated",
        "governance_status": "approved",
        "execution_status": "recovered",
        "operational_status": "stable",
        "stress_test": {
            "status": "passed",
            "success": True,
            "degradation_detected": False,
            "workflow_id": workflow_id,
        },
        "workflow_recovery_control": {
            "status": "recovered",
            "success": True,
            "workflow_id": workflow_id,
            "restored_state": {"workflow_id": workflow_id},
        },
        "metadata": {"phase": "10.2"},
    }
    values.update(overrides)
    return FailureRecoveryRequest(**values)


def test_failure_recovery_recovers_failure_and_metrics():
    status = RuntimeStatus()
    recovery = FailureRecovery(status=status)

    result = recovery.recover(_recovery_request())

    assert result.status == "recovered"
    assert result.success is True
    assert result.failure_detected is True
    assert result.recovery_required is True
    assert result.recovery_safe is True
    assert result.continuation_allowed is True
    assert "provider timeout" in result.failure_conditions

    metrics = status.failure_recovery_metrics()
    assert metrics["failure_recovery_status"] == "recovered"
    assert metrics["failure_recoveries_completed"] == 1
    assert metrics["failure_recovery_errors"] == 0
    assert metrics["recovery_safe"] is True


def test_failure_recovery_blocks_corrupt_runtime_and_instability():
    recovery = FailureRecovery()

    result = recovery.recover(
        _recovery_request(
            workflow_state={},
            restored_state={},
            workflow_recovery_control={},
            runtime_state={"status": "degraded", "loop_state": "stalled"},
            runtime_status="degraded",
            recovery_status="corrupt",
            continuation_status="broken",
            governance_status="pending",
            execution_status="blocked",
            instability_conditions=("runtime corruption",),
            blocking_conditions=("manual recovery required",),
        )
    )

    assert result.status == "blocked"
    assert result.continuation_allowed is False
    assert "workflow_integrity_required" in result.reasons
    assert "runtime_integrity_required" in result.reasons
    assert "recovery_status_required" in result.reasons
    assert "execution_continuity_required" in result.reasons
    assert "governance_consistency_required" in result.reasons
    assert "operational_stability_required" in result.reasons
    assert "failure_recovery_blocking_conditions_active" in result.reasons


def test_failure_recovery_blocks_invalid_recovery_requests():
    recovery = FailureRecovery()

    result = recovery.recover(
        _recovery_request(
            blocking_conditions=("recovery integrity missing",),
            ignore_runtime_failures_requested=True,
            minimize_corruption_risks_requested=True,
            overwrite_recovery_integrity_requested=True,
            alter_workflow_history_requested=True,
            continue_unsafe_execution_requested=True,
            recover_corrupt_runtime_requested=True,
            ignore_instability_conditions_requested=True,
            alter_governance_state_requested=True,
            hide_recovery_failures_requested=True,
            falsify_continuation_status_requested=True,
            ignore_blocking_conditions_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "runtime_failure_ignore_blocked" in result.reasons
    assert "corruption_risk_minimization_blocked" in result.reasons
    assert "recovery_integrity_overwrite_blocked" in result.reasons
    assert "workflow_history_alteration_blocked" in result.reasons
    assert "unsafe_execution_continuation_blocked" in result.reasons
    assert "corrupt_runtime_recovery_blocked" in result.reasons
    assert "instability_condition_ignore_blocked" in result.reasons
    assert "governance_state_alteration_blocked" in result.reasons
    assert "recovery_failure_concealment_blocked" in result.reasons
    assert "continuation_status_falsification_blocked" in result.reasons
    assert "blocking_condition_ignore_blocked" in result.reasons


def test_failure_recovery_blocks_unsafe_upstream_recovery_context():
    recovery = FailureRecovery()

    result = recovery.recover(
        _recovery_request(
            stress_test={
                "status": "blocked",
                "success": False,
                "degradation_detected": True,
                "failure_conditions": ("runtime_load_degraded",),
            },
            workflow_recovery_control={
                "status": "blocked",
                "success": False,
                "workflow_id": "10.2_FAILURE_RECOVERY.md",
            },
        )
    )

    assert result.status == "blocked"
    assert "runtime_integrity_required" in result.reasons
    assert "recovery_status_required" in result.reasons
    assert "stress_test_blocked" in result.failure_conditions
    assert "workflow_recovery_control_blocked" in result.failure_conditions


def test_failure_recovery_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    recovery = FailureRecovery(status=status)

    def broken_checks(*args, **kwargs):
        raise RuntimeError("failure recovery exploded")

    monkeypatch.setattr(recovery, "_checks", broken_checks)

    result = recovery.recover(_recovery_request())

    assert result.status == "error"
    assert "failure_recovery_error_contained" in result.reasons

    metrics = status.failure_recovery_metrics()
    assert metrics["failure_recovery_status"] == "error"
    assert metrics["failure_recovery_errors"] == 1
