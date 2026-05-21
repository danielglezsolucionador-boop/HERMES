from app.runner.production_hardening import (
    ProductionHardening,
    ProductionHardeningRequest,
)
from app.services.runtime_status import RuntimeStatus


def _hardening_request(**overrides):
    workflow_id = "10.6_PRODUCTION_HARDENING.md"
    values = {
        "hardening_id": "hardening-10-6",
        "workflow_id": workflow_id,
        "runtime_status": {"status": "online", "runner_status": "active"},
        "execution_status": {"status": "stable"},
        "governance_status": {"governance_status": "approved"},
        "workflow_status": {
            "workflow_status": "ready",
            "workflow_traceability_preserved": True,
        },
        "security_status": {"security_status": "protected"},
        "resilience_status": {"resilience_status": "resilient"},
        "stress_tests": {"status": "passed", "workflow_id": workflow_id},
        "failure_recovery": {"status": "recovered", "workflow_id": workflow_id},
        "restart_persistence": {"status": "restored", "workflow_id": workflow_id},
        "long_running_validation": {
            "status": "validated",
            "workflow_id": workflow_id,
        },
        "observability_base": {"status": "observed", "workflow_id": workflow_id},
        "metadata": {"phase": "10.6"},
    }
    values.update(overrides)
    return ProductionHardeningRequest(**values)


def test_production_hardening_applies_protections_and_metrics():
    status = RuntimeStatus()
    hardening = ProductionHardening(status=status)

    result = hardening.harden(_hardening_request())

    assert result.status == "hardened"
    assert result.success is True
    assert result.hardening_consistent is True
    assert result.continuation_allowed is True
    assert result.runtime_protected is True
    assert "runtime_protection" in result.protections_applied

    metrics = status.production_hardening_metrics()
    assert metrics["production_hardening_status"] == "hardened"
    assert metrics["production_hardenings_applied"] == 1
    assert metrics["production_hardening_errors"] == 0
    assert metrics["hardening_consistent"] is True


def test_production_hardening_blocks_runtime_and_security_risks():
    hardening = ProductionHardening()

    result = hardening.harden(
        _hardening_request(
            runtime_status={"status": "degraded"},
            execution_status={"status": "blocked"},
            governance_status={"governance_status": "pending"},
            security_status={"security_status": "exposed"},
            resilience_status={"resilience_status": "degraded"},
            workflow_status={
                "workflow_status": "blocked",
                "workflow_traceability_preserved": False,
            },
            runtime_risks=("runtime drift",),
            operational_vulnerabilities=("unbounded retry",),
            workflow_instability=("workflow instability",),
            governance_exposure=("governance conflict",),
            security_weaknesses=("missing guardrail",),
            blocking_conditions=("critical production block",),
        )
    )

    assert result.status == "blocked"
    assert result.continuation_allowed is False
    assert "runtime_protection_required" in result.reasons
    assert "execution_safety_required" in result.reasons
    assert "governance_protection_required" in result.reasons
    assert "security_stability_required" in result.reasons
    assert "operational_resilience_required" in result.reasons
    assert "workflow_integrity_required" in result.reasons
    assert "production_risks_detected" in result.reasons
    assert "production_blocking_conditions_active" in result.reasons


def test_production_hardening_blocks_override_requests():
    hardening = ProductionHardening()

    result = hardening.harden(
        _hardening_request(
            ignore_critical_risks_requested=True,
            minimize_instability_conditions_requested=True,
            overwrite_security_protections_requested=True,
            alter_governance_runtime_requested=True,
            invalidate_blocking_systems_requested=True,
            continue_unsafe_execution_requested=True,
            hide_runtime_vulnerabilities_requested=True,
            falsify_resilience_status_requested=True,
            ignore_governance_conflicts_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "critical_risk_ignore_blocked" in result.reasons
    assert "instability_condition_minimization_blocked" in result.reasons
    assert "security_protection_overwrite_blocked" in result.reasons
    assert "governance_runtime_alteration_blocked" in result.reasons
    assert "blocking_system_invalidation_blocked" in result.reasons
    assert "unsafe_execution_continuation_blocked" in result.reasons
    assert "runtime_vulnerability_concealment_blocked" in result.reasons
    assert "resilience_status_falsification_blocked" in result.reasons
    assert "governance_conflict_ignore_blocked" in result.reasons


def test_production_hardening_blocks_failed_upstream_context():
    hardening = ProductionHardening()

    result = hardening.harden(
        _hardening_request(
            stress_tests={
                "status": "blocked",
                "failure_conditions": ("load degradation",),
            },
            observability_base={
                "status": "blocked",
                "anomaly_conditions": ("hidden anomaly",),
            },
            long_running_validation={
                "status": "blocked",
                "failure_conditions": ("memory growth",),
            },
        )
    )

    assert result.status == "blocked"
    assert "failure_resistance_required" in result.reasons
    assert "stress_tests_blocked" in result.risk_conditions
    assert "observability_base_blocked" in result.risk_conditions
    assert "long_running_validation_blocked" in result.risk_conditions


def test_production_hardening_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    hardening = ProductionHardening(status=status)

    def broken_checks(*args, **kwargs):
        raise RuntimeError("production hardening exploded")

    monkeypatch.setattr(hardening, "_checks", broken_checks)

    result = hardening.harden(_hardening_request())

    assert result.status == "error"
    assert "production_hardening_error_contained" in result.reasons

    metrics = status.production_hardening_metrics()
    assert metrics["production_hardening_status"] == "error"
    assert metrics["production_hardening_errors"] == 1
