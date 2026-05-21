from app.runner.sentinel_audit_pipeline import (
    SentinelAuditPipeline,
    SentinelAuditRequest,
)
from app.services.runtime_status import RuntimeStatus


def _base_request(**overrides):
    data = {
        "execution_id": "execution-1",
        "task_id": "task-1",
        "execution_context": {"subphase": "7.1_SENTINEL_AUDIT_PIPELINE.md"},
        "modified_files": ("app/runner/sentinel_audit_pipeline.py",),
        "runtime_validation": "passed",
        "import_validation": "passed",
        "architecture_validation": "stable",
        "governance_validation": "approved",
        "security_observation": "clear",
        "risks_detected": ("none",),
        "blocking_conditions": ("none",),
        "governance_context": {"authority": "SENTINEL"},
    }
    data.update(overrides)
    return SentinelAuditRequest(**data)


def test_sentinel_audit_pipeline_approves_stable_workflow_and_metrics():
    status = RuntimeStatus()
    pipeline = SentinelAuditPipeline(status=status)

    result = pipeline.audit(_base_request())

    assert result.status == "approved"
    assert result.success is True
    assert result.audit_decision == "approve"
    assert result.runtime_valid is True
    assert result.imports_valid is True
    assert result.architecture_valid is True
    assert result.governance_valid is True
    assert result.security_observation_clear is True
    assert result.continuation_authorized is True
    assert result.audit_completed is True

    metrics = status.sentinel_audit_pipeline_metrics()
    assert metrics["sentinel_audit_pipeline_status"] == "approved"
    assert metrics["sentinel_audit_pipeline_completed"] == 1
    assert metrics["sentinel_audit_pipeline_errors"] == 0
    assert metrics["audit_decision"] == "approve"


def test_sentinel_audit_pipeline_conditionally_approves_with_risks():
    pipeline = SentinelAuditPipeline()

    result = pipeline.review(
        _base_request(
            risks_detected=("minor operational warning",),
            requested_decision="conditional_approve",
        )
    )

    assert result.status == "conditional_approved"
    assert result.audit_decision == "conditional_approve"
    assert result.continuation_authorized is True
    assert "sentinel_conditional_approval" in result.reasons


def test_sentinel_audit_pipeline_rejects_runtime_failures_and_blockers():
    pipeline = SentinelAuditPipeline()

    result = pipeline.audit(
        _base_request(
            runtime_validation="failed",
            architecture_validation="invalid",
            blocking_conditions=("runtime corruption",),
        )
    )

    assert result.status == "rejected"
    assert result.audit_decision == "reject"
    assert "runtime_validation_failed" in result.reasons
    assert "architecture_validation_failed" in result.reasons
    assert "blocking_conditions_active" in result.reasons
    assert result.continuation_authorized is False


def test_sentinel_audit_pipeline_escalates_security_observation():
    pipeline = SentinelAuditPipeline()

    result = pipeline.audit(
        _base_request(security_observation="critical")
    )

    assert result.status == "escalated"
    assert result.audit_decision == "escalate"
    assert result.security_escalation_required is True
    assert result.continuation_authorized is False


def test_sentinel_audit_pipeline_blocks_execution_authority_and_false_reporting():
    pipeline = SentinelAuditPipeline()

    result = pipeline.audit(
        _base_request(
            modify_workflow_requested=True,
            execute_productive_code_requested=True,
            alter_governance_requested=True,
            replace_centinela_requested=True,
            falsify_audit_status_requested=True,
            approve_corrupt_workflow_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "sentinel_execution_authority_blocked" in result.reasons
    assert "sentinel_productive_execution_blocked" in result.reasons
    assert "sentinel_governance_alteration_blocked" in result.reasons
    assert "centinela_replacement_blocked" in result.reasons
    assert "audit_status_falsification_blocked" in result.reasons
    assert "corrupt_workflow_approval_blocked" in result.reasons
    assert result.audit_completed is False


def test_sentinel_audit_pipeline_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    pipeline = SentinelAuditPipeline(status=status)

    def broken_validation(*args, **kwargs):
        raise RuntimeError("sentinel audit exploded")

    monkeypatch.setattr(pipeline, "_validation_reasons", broken_validation)

    result = pipeline.audit(_base_request())

    assert result.status == "error"
    assert "sentinel_audit_pipeline_error_contained" in result.reasons

    metrics = status.sentinel_audit_pipeline_metrics()
    assert metrics["sentinel_audit_pipeline_status"] == "error"
    assert metrics["sentinel_audit_pipeline_errors"] == 1
