from app.runner.observability_base import (
    ObservabilityBase,
    ObservabilityBaseRequest,
)
from app.services.runtime_status import RuntimeStatus


def _observability_request(**overrides):
    workflow_id = "10.5_OBSERVABILITY_BASE.md"
    values = {
        "observation_id": "observability-10-5",
        "workflow_id": workflow_id,
        "runtime_status": {"status": "online", "runner_status": "active"},
        "execution_status": {"status": "active"},
        "performance_metrics": {
            "pipeline_avg_ms": 120,
            "degradation_detected": False,
        },
        "governance_status": {"governance_status": "approved"},
        "continuity_status": {
            "continuation_status": "ready",
            "workflow_traceability_preserved": True,
        },
        "stress_tests": {"status": "passed", "workflow_id": workflow_id},
        "failure_recovery": {"status": "recovered", "workflow_id": workflow_id},
        "restart_persistence": {"status": "restored", "workflow_id": workflow_id},
        "long_running_validation": {
            "status": "validated",
            "workflow_id": workflow_id,
            "degradation_detected": False,
        },
        "metadata": {"phase": "10.5"},
    }
    values.update(overrides)
    return ObservabilityBaseRequest(**values)


def test_observability_base_creates_snapshot_and_metrics():
    status = RuntimeStatus()
    observer = ObservabilityBase(status=status)

    result = observer.observe(_observability_request())

    assert result.status == "observed"
    assert result.success is True
    assert result.observability_consistent is True
    assert result.continuation_allowed is True
    assert result.anomalies_detected is False

    metrics = status.observability_base_metrics()
    assert metrics["observability_base_status"] == "observed"
    assert metrics["observability_snapshots_created"] == 1
    assert metrics["observability_base_errors"] == 0
    assert metrics["observability_consistent"] is True


def test_observability_base_detects_anomalies_and_degradation():
    observer = ObservabilityBase()

    result = observer.observe(
        _observability_request(
            runtime_status={"status": "degraded"},
            performance_metrics={"degradation_detected": True},
            governance_status={"governance_status": "pending"},
            continuity_status={
                "continuation_status": "blocked",
                "workflow_traceability_preserved": False,
            },
            anomaly_signals=("runtime anomaly",),
            degradation_conditions=("memory degradation",),
        )
    )

    assert result.status == "blocked"
    assert result.degradation_detected is True
    assert "runtime_visibility_required" in result.reasons
    assert "performance_metrics_required" in result.reasons
    assert "governance_transparency_required" in result.reasons
    assert "continuity_visibility_required" in result.reasons
    assert "workflow_traceability_required" in result.reasons
    assert "observability_anomalies_detected" in result.reasons


def test_observability_base_blocks_false_observability_requests():
    observer = ObservabilityBase()

    result = observer.observe(
        _observability_request(
            blocking_conditions=("critical anomaly",),
            hide_runtime_degradation_requested=True,
            minimize_critical_anomalies_requested=True,
            falsify_operational_metrics_requested=True,
            ignore_execution_instability_requested=True,
            overwrite_observability_history_requested=True,
            alter_runtime_metrics_requested=True,
            hide_workflow_failures_requested=True,
            ignore_governance_conflicts_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "runtime_degradation_concealment_blocked" in result.reasons
    assert "critical_anomaly_minimization_blocked" in result.reasons
    assert "operational_metric_falsification_blocked" in result.reasons
    assert "execution_instability_ignore_blocked" in result.reasons
    assert "observability_history_overwrite_blocked" in result.reasons
    assert "runtime_metric_alteration_blocked" in result.reasons
    assert "workflow_failure_concealment_blocked" in result.reasons
    assert "governance_conflict_ignore_blocked" in result.reasons


def test_observability_base_blocks_failed_upstream_metrics():
    observer = ObservabilityBase()

    result = observer.observe(
        _observability_request(
            stress_tests={
                "status": "blocked",
                "failure_conditions": ("runtime_load_degraded",),
            },
            long_running_validation={
                "status": "blocked",
                "failure_conditions": ("memory_growth_degraded",),
                "degradation_detected": True,
            },
        )
    )

    assert result.status == "blocked"
    assert "operational_stability_required" in result.reasons
    assert "stress_tests_blocked" in result.anomaly_conditions
    assert "long_running_validation_blocked" in result.anomaly_conditions
    assert result.degradation_detected is True


def test_observability_base_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    observer = ObservabilityBase(status=status)

    def broken_checks(*args, **kwargs):
        raise RuntimeError("observability exploded")

    monkeypatch.setattr(observer, "_checks", broken_checks)

    result = observer.observe(_observability_request())

    assert result.status == "error"
    assert "observability_base_error_contained" in result.reasons

    metrics = status.observability_base_metrics()
    assert metrics["observability_base_status"] == "error"
    assert metrics["observability_base_errors"] == 1
