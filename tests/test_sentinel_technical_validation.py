from app.runner.sentinel_audit_pipeline import (
    SentinelAuditPipeline,
    SentinelAuditRequest,
)
from app.runner.sentinel_technical_validation import (
    SentinelTechnicalValidation,
    SentinelTechnicalValidationRequest,
)
from app.services.runtime_status import RuntimeStatus


def _base_request(**overrides):
    data = {
        "execution_id": "execution-1",
        "task_id": "task-1",
        "modified_files": ("app/runner/sentinel_technical_validation.py",),
        "import_validation": "passed",
        "syntax_validation": "passed",
        "runtime_validation": "passed",
        "architecture_validation": "stable",
        "execution_validation": "valid",
        "governance_validation": "approved",
        "security_observation": "clear",
        "validation_commands": (
            "python -m py_compile app/runner/sentinel_technical_validation.py",
            "python -c import main",
            "pytest",
        ),
        "runtime_status": "active",
        "architecture_status": "stable",
        "governance_status": "approved",
        "risks_detected": ("none",),
        "blocking_conditions": ("none",),
    }
    data.update(overrides)
    return SentinelTechnicalValidationRequest(**data)


def test_sentinel_technical_validation_validates_safe_workflow_and_metrics():
    status = RuntimeStatus()
    validator = SentinelTechnicalValidation(status=status)

    result = validator.validate(_base_request())

    assert result.status == "validated"
    assert result.success is True
    assert result.import_valid is True
    assert result.syntax_valid is True
    assert result.runtime_valid is True
    assert result.architecture_valid is True
    assert result.execution_integrity_valid is True
    assert result.workflow_safe is True
    assert result.audit_decision_recommendation == "approve"

    metrics = status.sentinel_technical_validation_metrics()
    assert metrics["sentinel_technical_validation_status"] == "validated"
    assert metrics["sentinel_technical_validation_validated"] == 1
    assert metrics["sentinel_technical_validation_errors"] == 0
    assert metrics["workflow_safe"] is True


def test_sentinel_technical_validation_blocks_import_syntax_and_runtime_failures():
    validator = SentinelTechnicalValidation()

    result = validator.validate(
        _base_request(
            import_validation="failed",
            syntax_validation="failed",
            runtime_validation="critical",
            blocking_conditions=("runtime corruption",),
            runtime_status="critical",
        )
    )

    assert result.status == "blocked"
    assert "import_validation_failed" in result.reasons
    assert "syntax_validation_failed" in result.reasons
    assert "runtime_validation_failed" in result.reasons
    assert "blocking_conditions_active" in result.reasons
    assert "runtime_status_unsafe" in result.reasons
    assert result.workflow_safe is False
    assert result.audit_decision_recommendation == "reject"


def test_sentinel_technical_validation_recommends_conditional_for_risks():
    validator = SentinelTechnicalValidation()

    result = validator.inspect(
        _base_request(risks_detected=("minor architecture warning",))
    )

    assert result.status == "validated"
    assert result.success is True
    assert result.workflow_safe is True
    assert result.audit_decision_recommendation == "conditional_approve"


def test_sentinel_technical_validation_recommends_security_escalation():
    validator = SentinelTechnicalValidation()

    result = validator.validate(
        _base_request(security_observation="critical")
    )

    assert result.status == "blocked"
    assert "security_validation_failed" in result.reasons
    assert result.security_escalation_recommended is True
    assert result.audit_decision_recommendation == "escalate"


def test_sentinel_technical_validation_blocks_false_validation_requests():
    validator = SentinelTechnicalValidation()

    result = validator.validate(
        _base_request(
            falsify_validations_requested=True,
            ignore_runtime_failures_requested=True,
            hide_inconsistencies_requested=True,
            minimize_risks_requested=True,
            approve_corrupt_workflow_requested=True,
            alter_execution_runtime_requested=True,
            risks_detected=("real risk",),
        )
    )

    assert result.status == "blocked"
    assert "false_validation_blocked" in result.reasons
    assert "runtime_failure_ignored_blocked" in result.reasons
    assert "inconsistency_concealment_blocked" in result.reasons
    assert "risk_minimization_blocked" in result.reasons
    assert "corrupt_workflow_approval_blocked" in result.reasons
    assert "execution_runtime_alteration_blocked" in result.reasons


def test_sentinel_technical_validation_respects_blocking_audit_pipeline():
    audit = SentinelAuditPipeline().audit(
        SentinelAuditRequest(
            execution_id="execution-1",
            execution_context={"subphase": "7.2"},
            modified_files=("app/runner/sentinel_technical_validation.py",),
            runtime_validation="failed",
            import_validation="passed",
            architecture_validation="stable",
            governance_validation="approved",
            security_observation="clear",
            blocking_conditions=("runtime corruption",),
        )
    )
    validator = SentinelTechnicalValidation()

    result = validator.validate(_base_request(audit_pipeline=audit))

    assert audit.status == "rejected"
    assert result.status == "blocked"
    assert "sentinel_audit_pipeline_blocks_validation" in result.reasons


def test_sentinel_technical_validation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    validator = SentinelTechnicalValidation(status=status)

    def broken_validation(*args, **kwargs):
        raise RuntimeError("technical validation exploded")

    monkeypatch.setattr(validator, "_validation_reasons", broken_validation)

    result = validator.validate(_base_request())

    assert result.status == "error"
    assert "sentinel_technical_validation_error_contained" in result.reasons

    metrics = status.sentinel_technical_validation_metrics()
    assert metrics["sentinel_technical_validation_status"] == "error"
    assert metrics["sentinel_technical_validation_errors"] == 1
