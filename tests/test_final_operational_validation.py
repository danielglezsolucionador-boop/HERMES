from app.runner.final_operational_validation import (
    FinalOperationalValidation,
    FinalOperationalValidationRequest,
)
from app.services.runtime_status import RuntimeStatus


def _final_request(**overrides):
    workflow_id = "10.7_FINAL_OPERATIONAL_VALIDATION.md"
    values = {
        "validation_id": "final-10-7",
        "workflow_id": workflow_id,
        "runtime_status": {"status": "online"},
        "workflow_status": {"workflow_status": "validated"},
        "governance_status": {"governance_status": "approved"},
        "audit_status": {"audit_status": "approved"},
        "security_status": {"security_status": "protected"},
        "knowledge_core_status": {"knowledge_core_status": "validated"},
        "stability_status": {"stability_status": "stable"},
        "authority_status": {
            "ceo_authority_valid": True,
            "cerebro_communication_valid": True,
            "sentinel_audit_authority_valid": True,
            "centinela_security_authority_valid": True,
        },
        "execution_status": {"execution_status": "completed"},
        "workflow_validation": {"status": "validated"},
        "governance_validation": {"status": "approved"},
        "audit_validation": {"status": "approved"},
        "security_validation": {"status": "protected"},
        "knowledge_core_validation": {"status": "validated"},
        "stress_tests": {"status": "passed"},
        "failure_recovery": {"status": "recovered"},
        "restart_persistence": {"status": "restored"},
        "long_running_validation": {"status": "validated"},
        "observability_base": {"status": "observed"},
        "production_hardening": {"status": "hardened"},
        "metadata": {"phase": "10.7"},
    }
    values.update(overrides)
    return FinalOperationalValidationRequest(**values)


def test_final_operational_validation_marks_runtime_ready_and_metrics():
    status = RuntimeStatus()
    validator = FinalOperationalValidation(status=status)

    result = validator.validate(_final_request())

    assert result.status == "ready"
    assert result.success is True
    assert result.final_readiness_valid is True
    assert result.production_safe is True
    assert result.final_report["FINAL DECISION"] == "production_ready"
    assert "runtime_validation" in result.validations_executed

    metrics = status.final_operational_validation_metrics()
    assert metrics["final_operational_validation_status"] == "ready"
    assert metrics["final_operational_validations_ready"] == 1
    assert metrics["final_operational_validation_errors"] == 0
    assert metrics["final_readiness_valid"] is True


def test_final_operational_validation_blocks_unstable_runtime():
    validator = FinalOperationalValidation()

    result = validator.validate(
        _final_request(
            runtime_status={"status": "degraded"},
            workflow_status={"workflow_status": "blocked"},
            governance_status={"governance_status": "pending"},
            audit_status={"audit_status": "failed"},
            security_status={"security_status": "bypassed"},
            knowledge_core_status={"knowledge_core_status": "missing"},
            stability_status={"stability_status": "degraded"},
            authority_status={
                "ceo_authority_valid": False,
                "cerebro_communication_valid": True,
                "sentinel_audit_authority_valid": True,
                "centinela_security_authority_valid": True,
            },
            execution_status={"execution_status": "failed"},
            risks=("runtime unstable",),
            blockers=("manual review required",),
        )
    )

    assert result.status == "blocked"
    assert result.continuation_allowed is False
    assert "runtime_validation_required" in result.reasons
    assert "workflow_validation_required" in result.reasons
    assert "governance_validation_required" in result.reasons
    assert "audit_validation_required" in result.reasons
    assert "security_validation_required" in result.reasons
    assert "knowledge_core_validation_required" in result.reasons
    assert "stability_validation_required" in result.reasons
    assert "authority_validation_required" in result.reasons
    assert "execution_validation_required" in result.reasons


def test_final_operational_validation_blocks_false_readiness_requests():
    validator = FinalOperationalValidation()

    result = validator.validate(
        _final_request(
            approve_unstable_runtime_requested=True,
            hide_critical_failures_requested=True,
            ignore_governance_conflicts_requested=True,
            falsify_readiness_requested=True,
            continue_unsafe_production_requested=True,
            override_authority_requested=True,
            skip_audit_requested=True,
            bypass_security_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "unstable_runtime_approval_blocked" in result.reasons
    assert "critical_failure_concealment_blocked" in result.reasons
    assert "governance_conflict_ignore_blocked" in result.reasons
    assert "readiness_falsification_blocked" in result.reasons
    assert "unsafe_production_continuation_blocked" in result.reasons
    assert "authority_override_blocked" in result.reasons
    assert "audit_skip_blocked" in result.reasons
    assert "security_bypass_blocked" in result.reasons


def test_final_operational_validation_blocks_failed_stability_context():
    validator = FinalOperationalValidation()

    result = validator.validate(
        _final_request(
            stress_tests={
                "status": "blocked",
                "failure_conditions": ("load failure",),
            },
            observability_base={
                "status": "blocked",
                "anomaly_conditions": ("runtime anomaly",),
            },
            production_hardening={
                "status": "blocked",
                "risk_conditions": ("production risk",),
            },
        )
    )

    assert result.status == "blocked"
    assert "stability_validation_required" in result.reasons
    assert "stress_tests_blocked" in result.risks
    assert "observability_base_blocked" in result.risks
    assert "production_hardening_blocked" in result.risks


def test_final_operational_validation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    validator = FinalOperationalValidation(status=status)

    def broken_checks(*args, **kwargs):
        raise RuntimeError("final validation exploded")

    monkeypatch.setattr(validator, "_checks", broken_checks)

    result = validator.validate(_final_request())

    assert result.status == "error"
    assert "final_operational_validation_error_contained" in result.reasons

    metrics = status.final_operational_validation_metrics()
    assert metrics["final_operational_validation_status"] == "error"
    assert metrics["final_operational_validation_errors"] == 1
