from app.runner.stress_tests import StressTestRequest, StressTests
from app.services.runtime_status import RuntimeStatus


def _stress_request(**overrides):
    values = {
        "stress_id": "stress-10-1",
        "workflow_id": "10.1_STRESS_TESTS.md",
        "runtime_status": "online",
        "continuation_status": "ready",
        "governance_status": "approved",
        "recovery_status": "ready",
        "runtime_state": {"status": "online", "loop_state": "active"},
        "runtime_load": 0.42,
        "max_runtime_load": 0.85,
        "workflow_concurrency": 3,
        "max_workflow_concurrency": 8,
        "duration_seconds": 180.0,
        "execution_cycles": 120,
        "successful_cycles": 120,
        "failed_cycles": 0,
        "max_failed_cycles": 0,
        "avg_execution_ms": 120,
        "max_execution_ms": 500,
        "memory_usage_mb": 128.0,
        "max_memory_mb": 512.0,
        "memory_growth_mb": 8.0,
        "max_memory_growth_mb": 64.0,
        "workflow_validation": {
            "status": "validated",
            "success": True,
            "workflow_safe": True,
            "workflow_id": "10.1_STRESS_TESTS.md",
        },
        "metadata": {"phase": "10.1"},
    }
    values.update(overrides)
    return StressTestRequest(**values)


def test_stress_tests_pass_stable_runtime_and_metrics():
    status = RuntimeStatus()
    stress_tests = StressTests(status=status)

    result = stress_tests.evaluate(_stress_request())

    assert result.status == "passed"
    assert result.success is True
    assert result.stress_safe is True
    assert result.continuation_allowed is True
    assert result.degradation_detected is False

    metrics = status.stress_tests_metrics()
    assert metrics["stress_test_status"] == "passed"
    assert metrics["stress_tests_passed"] == 1
    assert metrics["stress_test_errors"] == 0
    assert metrics["stress_safe"] is True


def test_stress_tests_detect_runtime_memory_and_performance_degradation():
    stress_tests = StressTests()

    result = stress_tests.evaluate(
        _stress_request(
            runtime_status="degraded",
            runtime_state={"status": "degraded", "loop_state": "stalled"},
            runtime_load=0.96,
            workflow_concurrency=12,
            failed_cycles=3,
            max_failed_cycles=0,
            avg_execution_ms=900,
            memory_usage_mb=900.0,
            memory_growth_mb=128.0,
            degradation_signals=("runtime slowdown",),
        )
    )

    assert result.status == "blocked"
    assert result.continuation_allowed is False
    assert "runtime_integrity_required" in result.reasons
    assert "execution_continuity_required" in result.reasons
    assert "performance_status_required" in result.reasons
    assert "memory_stability_required" in result.reasons
    assert "stress_failure_conditions_detected" in result.reasons
    assert "runtime_load_degraded" in result.failure_conditions
    assert "execution_slowdown_detected" in result.failure_conditions
    assert "memory_usage_degraded" in result.failure_conditions
    assert "runtime_load" in result.bottlenecks


def test_stress_tests_block_false_stability_requests():
    stress_tests = StressTests()

    result = stress_tests.evaluate(
        _stress_request(
            failure_conditions=("runtime degradation",),
            ignore_runtime_degradation_requested=True,
            minimize_performance_failures_requested=True,
            hide_execution_instability_requested=True,
            overwrite_operational_limits_requested=True,
            continue_corrupt_runtime_requested=True,
            falsify_stress_results_requested=True,
            alter_stress_metrics_requested=True,
            ignore_failure_conditions_requested=True,
            minimize_instability_risks_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "runtime_degradation_ignore_blocked" in result.reasons
    assert "performance_failure_minimization_blocked" in result.reasons
    assert "execution_instability_concealment_blocked" in result.reasons
    assert "operational_limit_overwrite_blocked" in result.reasons
    assert "corrupt_runtime_continuation_blocked" in result.reasons
    assert "stress_result_falsification_blocked" in result.reasons
    assert "stress_metric_alteration_blocked" in result.reasons
    assert "failure_condition_ignore_blocked" in result.reasons
    assert "instability_risk_minimization_blocked" in result.reasons


def test_stress_tests_block_governance_recovery_and_validation_drift():
    stress_tests = StressTests()

    result = stress_tests.evaluate(
        _stress_request(
            governance_status="pending",
            recovery_status="unavailable",
            workflow_validation={
                "status": "blocked",
                "success": False,
                "workflow_safe": False,
            },
        )
    )

    assert result.status == "blocked"
    assert "governance_stability_required" in result.reasons
    assert "recovery_status_required" in result.reasons
    assert "workflow_validation_failed" in result.failure_conditions
    assert "governance_instability_detected" in result.failure_conditions
    assert "recovery_status_unavailable" in result.failure_conditions


def test_stress_tests_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    stress_tests = StressTests(status=status)

    def broken_checks(*args, **kwargs):
        raise RuntimeError("stress tests exploded")

    monkeypatch.setattr(stress_tests, "_checks", broken_checks)

    result = stress_tests.evaluate(_stress_request())

    assert result.status == "error"
    assert "stress_test_error_contained" in result.reasons

    metrics = status.stress_tests_metrics()
    assert metrics["stress_test_status"] == "error"
    assert metrics["stress_test_errors"] == 1
