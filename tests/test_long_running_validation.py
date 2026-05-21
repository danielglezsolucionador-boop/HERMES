from app.runner.long_running_validation import (
    LongRunningValidation,
    LongRunningValidationRequest,
)
from app.services.runtime_status import RuntimeStatus


def _long_running_request(**overrides):
    workflow_id = "10.4_LONG_RUNNING_VALIDATION.md"
    values = {
        "validation_id": "long-running-10-4",
        "workflow_id": workflow_id,
        "runtime_duration_seconds": 7200.0,
        "min_runtime_duration_seconds": 3600.0,
        "runtime_status": "online",
        "continuation_status": "ready",
        "governance_status": "approved",
        "recovery_status": "recovered",
        "runtime_state": {"status": "online", "loop_state": "active"},
        "execution_cycles": 240,
        "successful_cycles": 240,
        "failed_cycles": 0,
        "max_failed_cycles": 0,
        "avg_execution_ms": 180,
        "max_execution_ms": 750,
        "memory_usage_mb": 192.0,
        "max_memory_mb": 512.0,
        "memory_growth_mb": 16.0,
        "max_memory_growth_mb": 96.0,
        "stress_test": {
            "status": "passed",
            "success": True,
            "workflow_id": workflow_id,
            "degradation_detected": False,
        },
        "failure_recovery": {
            "status": "recovered",
            "success": True,
            "workflow_id": workflow_id,
        },
        "restart_persistence": {
            "status": "restored",
            "success": True,
            "workflow_id": workflow_id,
        },
        "metadata": {"phase": "10.4"},
    }
    values.update(overrides)
    return LongRunningValidationRequest(**values)


def test_long_running_validation_validates_stable_runtime_and_metrics():
    status = RuntimeStatus()
    validator = LongRunningValidation(status=status)

    result = validator.validate(_long_running_request())

    assert result.status == "validated"
    assert result.success is True
    assert result.long_running_safe is True
    assert result.continuation_allowed is True
    assert result.degradation_detected is False

    metrics = status.long_running_validation_metrics()
    assert metrics["long_running_validation_status"] == "validated"
    assert metrics["long_running_validations_validated"] == 1
    assert metrics["long_running_validation_errors"] == 0
    assert metrics["long_running_safe"] is True


def test_long_running_validation_detects_persistent_degradation():
    validator = LongRunningValidation()

    result = validator.validate(
        _long_running_request(
            runtime_duration_seconds=120.0,
            runtime_status="degraded",
            runtime_state={"status": "degraded", "loop_state": "stalled"},
            continuation_status="broken",
            governance_status="pending",
            recovery_status="blocked",
            failed_cycles=5,
            avg_execution_ms=1200,
            memory_usage_mb=900.0,
            memory_growth_mb=256.0,
            degradation_signals=("persistent runtime degradation",),
        )
    )

    assert result.status == "blocked"
    assert result.continuation_allowed is False
    assert "runtime_duration_required" in result.reasons
    assert "runtime_integrity_required" in result.reasons
    assert "execution_continuity_required" in result.reasons
    assert "performance_stability_required" in result.reasons
    assert "memory_consistency_required" in result.reasons
    assert "governance_stability_required" in result.reasons
    assert "recovery_status_required" in result.reasons
    assert "long_running_degradation_detected" in result.reasons
    assert "execution_slowdown_detected" in result.failure_conditions
    assert "memory_usage_degraded" in result.failure_conditions


def test_long_running_validation_blocks_false_stability_requests():
    validator = LongRunningValidation()

    result = validator.validate(
        _long_running_request(
            failure_conditions=("runtime instability",),
            ignore_runtime_degradation_requested=True,
            minimize_instability_risks_requested=True,
            hide_execution_slowdown_requested=True,
            overwrite_operational_limits_requested=True,
            continue_corrupt_runtime_requested=True,
            falsify_runtime_duration_requested=True,
            alter_runtime_metrics_requested=True,
            ignore_persistent_degradation_requested=True,
            minimize_instability_conditions_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "runtime_degradation_ignore_blocked" in result.reasons
    assert "instability_risk_minimization_blocked" in result.reasons
    assert "execution_slowdown_concealment_blocked" in result.reasons
    assert "operational_limit_overwrite_blocked" in result.reasons
    assert "corrupt_runtime_continuation_blocked" in result.reasons
    assert "runtime_duration_falsification_blocked" in result.reasons
    assert "runtime_metric_alteration_blocked" in result.reasons
    assert "persistent_degradation_ignore_blocked" in result.reasons
    assert "instability_condition_minimization_blocked" in result.reasons


def test_long_running_validation_blocks_failed_upstream_context():
    validator = LongRunningValidation()

    result = validator.validate(
        _long_running_request(
            stress_test={"status": "blocked", "failure_conditions": ("load",)},
            failure_recovery={"status": "blocked"},
            restart_persistence={
                "status": "blocked",
                "restart_conditions": ("restart drift",),
            },
        )
    )

    assert result.status == "blocked"
    assert "runtime_integrity_required" in result.reasons
    assert "operational_resilience_required" in result.reasons
    assert "stress_blocked" in result.failure_conditions
    assert "restart_persistence_blocked" in result.failure_conditions


def test_long_running_validation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    validator = LongRunningValidation(status=status)

    def broken_checks(*args, **kwargs):
        raise RuntimeError("long running validation exploded")

    monkeypatch.setattr(validator, "_checks", broken_checks)

    result = validator.validate(_long_running_request())

    assert result.status == "error"
    assert "long_running_validation_error_contained" in result.reasons

    metrics = status.long_running_validation_metrics()
    assert metrics["long_running_validation_status"] == "error"
    assert metrics["long_running_validation_errors"] == 1
