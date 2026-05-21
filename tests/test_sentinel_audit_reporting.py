from app.runner.sentinel_audit_reporting import (
    REQUIRED_REPORT_SECTIONS,
    SentinelAuditReporting,
    SentinelAuditReportingRequest,
)
from app.services.runtime_status import RuntimeStatus


def _base_request(**overrides):
    data = {
        "audit_id": "audit-1",
        "execution_id": "execution-1",
        "task_id": "task-1",
        "audit_status": "approved",
        "execution_context": {
            "subphase": "7.4_SENTINEL_AUDIT_REPORTING.md"
        },
        "validations_executed": (
            "python -m py_compile app/runner/sentinel_audit_reporting.py",
            "python -c import main",
            "pytest",
        ),
        "runtime_status": "active",
        "risks_detected": ("no_known_risks",),
        "blocking_conditions": ("none",),
        "governance_status": "approved",
        "security_status": "clear",
        "final_decision": "approve",
        "continuity_status": "authorized",
    }
    data.update(overrides)
    return SentinelAuditReportingRequest(**data)


def test_sentinel_audit_reporting_generates_required_report_and_metrics():
    status = RuntimeStatus()
    reporting = SentinelAuditReporting(status=status)

    result = reporting.generate(_base_request())

    assert result.status == "generated"
    assert result.success is True
    assert result.report_complete is True
    assert result.audit_transparency_preserved is True
    assert result.runtime_visibility_preserved is True
    assert result.execution_integrity_reported is True
    assert result.governance_consistency_preserved is True
    for section in REQUIRED_REPORT_SECTIONS:
        assert f"{section}:" in result.report_text

    metrics = status.sentinel_audit_reporting_metrics()
    assert metrics["sentinel_audit_reporting_status"] == "generated"
    assert metrics["sentinel_audit_reports_generated"] == 1
    assert metrics["sentinel_audit_reporting_errors"] == 0
    assert metrics["report_complete"] is True


def test_sentinel_audit_reporting_builds_report_from_existing_audit_evidence():
    reporting = SentinelAuditReporting()

    result = reporting.report(
        SentinelAuditReportingRequest(
            audit_pipeline={
                "audit_id": "audit-2",
                "status": "approved",
                "execution_id": "execution-2",
                "task_id": "task-2",
                "execution_context": {"subphase": "7.4"},
                "governance_valid": True,
                "security_observation_clear": True,
                "continuation_authorized": True,
                "audit_decision": "approve",
                "risks_detected": ["no_known_risks"],
                "blocking_conditions": ["none"],
            },
            technical_validation={
                "validation_commands": ["pytest -q"],
                "report_payload": {"runtime_status": "active"},
            },
        )
    )

    assert result.status == "generated"
    assert result.audit_id == "audit-2"
    assert result.execution_id == "execution-2"
    assert result.runtime_status == "active"
    assert result.governance_status == "approved"
    assert result.security_status == "clear"
    assert result.final_decision == "approve"
    assert result.continuity_status == "authorized"
    assert "pytest -q" in result.validations_executed


def test_sentinel_audit_reporting_blocks_dishonest_or_unsafe_reporting():
    reporting = SentinelAuditReporting()

    result = reporting.generate(
        _base_request(
            runtime_status="failed",
            risks_detected=("runtime corruption",),
            final_decision="approve",
            hide_inconsistencies_requested=True,
            minimize_runtime_risks_requested=True,
            falsify_audit_status_requested=True,
            approve_unsafe_execution_requested=True,
            alter_governance_reporting_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert result.report_complete is False
    assert "technical_inconsistency_concealment_blocked" in result.reasons
    assert "runtime_risk_minimization_blocked" in result.reasons
    assert "audit_status_falsification_blocked" in result.reasons
    assert "unsafe_execution_approval_blocked" in result.reasons
    assert "governance_reporting_alteration_blocked" in result.reasons
    assert "unsafe_runtime_approval_report_blocked" in result.reasons


def test_sentinel_audit_reporting_blocks_incomplete_reports():
    reporting = SentinelAuditReporting()

    result = reporting.generate(
        SentinelAuditReportingRequest(
            audit_status="approved",
            execution_context={"subphase": "7.4"},
        )
    )

    assert result.status == "blocked"
    assert "validations_executed_required" in result.reasons
    assert "runtime_status_required" in result.reasons
    assert "governance_status_required" in result.reasons
    assert "security_status_required" in result.reasons
    assert "final_decision_required" in result.reasons
    assert "continuity_status_required" in result.reasons


def test_sentinel_audit_reporting_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    reporting = SentinelAuditReporting(status=status)

    def broken_report_data(*args, **kwargs):
        raise RuntimeError("audit reporting exploded")

    monkeypatch.setattr(reporting, "_report_data", broken_report_data)

    result = reporting.generate(_base_request())

    assert result.status == "error"
    assert "sentinel_audit_reporting_error_contained" in result.reasons

    metrics = status.sentinel_audit_reporting_metrics()
    assert metrics["sentinel_audit_reporting_status"] == "error"
    assert metrics["sentinel_audit_reporting_errors"] == 1
