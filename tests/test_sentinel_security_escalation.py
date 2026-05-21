from app.runner.sentinel_security_escalation import (
    SentinelSecurityEscalationHook,
    SentinelSecurityEscalationRequest,
)
from app.services.runtime_status import RuntimeStatus


def _base_request(**overrides):
    data = {
        "execution_id": "execution-1",
        "task_id": "task-1",
        "execution_context": {
            "subphase": "7.3_SENTINEL_SECURITY_ESCALATION_HOOK.md"
        },
        "threat_detection": "clear",
        "security_observation": "clear",
        "execution_analysis": {"runtime": "stable"},
        "governance_impact": {"authority": "CENTINELA"},
        "threat_severity": "clear",
        "runtime_status": "active",
        "quarantine_status": "none",
        "blocking_conditions": (),
        "suspicious_modifications": (),
        "detected_threats": (),
    }
    data.update(overrides)
    return SentinelSecurityEscalationRequest(**data)


def test_sentinel_security_escalation_reports_clear_state_and_metrics():
    status = RuntimeStatus()
    hook = SentinelSecurityEscalationHook(status=status)

    result = hook.evaluate(_base_request())

    assert result.status == "clear"
    assert result.success is True
    assert result.threat_detected is False
    assert result.escalation_required is False
    assert result.centinela_escalation_prepared is False
    assert result.continuation_blocked is False
    assert result.runtime_integrity_preserved is True

    metrics = status.sentinel_security_escalation_metrics()
    assert metrics["sentinel_security_escalation_status"] == "clear"
    assert metrics["sentinel_security_escalation_clear"] == 1
    assert metrics["sentinel_security_escalation_errors"] == 0
    assert metrics["target_authority"] == "CENTINELA"


def test_sentinel_security_escalation_prepares_centinela_escalation():
    hook = SentinelSecurityEscalationHook()

    result = hook.escalate(
        _base_request(
            detected_threats=("runtime compromise detected",),
            suspicious_modifications=("app/runner/runtime_loop.py",),
            blocking_conditions=("runtime compromise",),
            threat_severity="critical",
            quarantine_status="active",
        )
    )

    assert result.status == "escalated"
    assert result.success is True
    assert result.threat_detected is True
    assert result.escalation_required is True
    assert result.centinela_escalation_prepared is True
    assert result.continuation_blocked is True
    assert result.quarantine_recommended is True
    assert result.target_authority == "CENTINELA"
    assert "runtime compromise detected" in result.detected_threats


def test_sentinel_security_escalation_uses_audit_and_technical_signals():
    hook = SentinelSecurityEscalationHook()

    result = hook.evaluate(
        _base_request(
            technical_validation={
                "validation_id": "validation-1",
                "security_escalation_recommended": True,
            },
            audit_pipeline={
                "audit_id": "audit-1",
                "audit_decision": "escalate",
            },
        )
    )

    assert result.status == "escalated"
    assert result.threat_severity == "critical"
    assert result.escalation_payload["technical_validation_id"] == (
        "validation-1"
    )
    assert result.escalation_payload["audit_id"] == "audit-1"


def test_sentinel_security_escalation_blocks_unsafe_authority_requests():
    hook = SentinelSecurityEscalationHook()

    result = hook.evaluate(
        _base_request(
            target_authority="HERMES",
            detected_threats=("secret leak",),
            resolve_threat_requested=True,
            replace_centinela_requested=True,
            unlock_quarantine_requested=True,
            alter_governance_requested=True,
            falsify_severity_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert result.centinela_escalation_prepared is False
    assert result.continuation_blocked is True
    assert "centinela_authority_required" in result.reasons
    assert "sentinel_self_resolution_blocked" in result.reasons
    assert "centinela_replacement_blocked" in result.reasons
    assert "quarantine_unlock_blocked" in result.reasons
    assert "security_governance_alteration_blocked" in result.reasons
    assert "security_severity_falsification_blocked" in result.reasons


def test_sentinel_security_escalation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    hook = SentinelSecurityEscalationHook(status=status)

    def broken_validation(*args, **kwargs):
        raise RuntimeError("security escalation exploded")

    monkeypatch.setattr(hook, "_validation_reasons", broken_validation)

    result = hook.evaluate(_base_request())

    assert result.status == "error"
    assert "sentinel_security_escalation_error_contained" in result.reasons

    metrics = status.sentinel_security_escalation_metrics()
    assert metrics["sentinel_security_escalation_status"] == "error"
    assert metrics["sentinel_security_escalation_errors"] == 1
