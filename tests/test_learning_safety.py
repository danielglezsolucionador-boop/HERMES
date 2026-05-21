from app.runner.learning_safety import LearningSafety, LearningSafetyRequest
from app.services.runtime_status import RuntimeStatus


def _valid_memory_record(**overrides):
    record = {
        "memory_id": "memory-1",
        "memory_type": "execution",
        "timestamp": "2026-05-21T00:00:00+00:00",
        "memory_context": {"execution_id": "execution-1"},
    }
    record.update(overrides)
    return record


def test_learning_safety_allows_safe_learning_and_metrics():
    status = RuntimeStatus()
    safety = LearningSafety(status=status)

    result = safety.validate(
        LearningSafetyRequest(
            learning_type="execution",
            risk_level="low",
            governance_status="approved",
            validation_status="validated",
            audit_status="approved",
            security_status="safe",
            runtime_state={"state": "active"},
            application_requested=True,
            learning_candidate={"learning_id": "learning-1"},
        )
    )

    assert result.status == "safe_learning"
    assert result.success is True
    assert result.application_status == "allowed"
    assert result.learning_control == "learning_allowed"
    assert result.human_authority_preserved is True

    metrics = status.learning_safety_metrics()
    assert metrics["learning_safety_status"] == "safe_learning"
    assert metrics["learning_safety_safe"] == 1
    assert metrics["learning_safety_errors"] == 0


def test_learning_safety_warns_on_runtime_instability_without_blocking():
    safety = LearningSafety()

    result = safety.validate(
        LearningSafetyRequest(
            learning_type="execution",
            runtime_instability=True,
            audit_status="approved_with_warnings",
            risk_level="elevated",
        )
    )

    assert result.status == "warning_learning"
    assert result.success is True
    assert result.application_status == "limited"
    assert "runtime_instability_warning" in result.reasons
    assert "elevated_risk_warning" in result.reasons


def test_learning_safety_blocks_governance_autonomy_and_architecture_learning():
    safety = LearningSafety()

    result = safety.validate(
        LearningSafetyRequest(
            learning_type="autonomy",
            governance_modification=True,
            autonomy_expansion=True,
            architecture_mutation=True,
            authority_modification=True,
            blocking_rule_modification=True,
        )
    )

    assert result.status == "blocked_learning"
    assert result.success is False
    assert "governance_learning_blocked" in result.reasons
    assert "autonomy_learning_blocked" in result.reasons
    assert "architecture_learning_blocked" in result.reasons
    assert "authority_modification_blocked" in result.reasons
    assert "blocking_rule_modification_blocked" in result.reasons


def test_learning_safety_blocks_corrupt_memory_reuse():
    safety = LearningSafety()

    result = safety.validate(
        LearningSafetyRequest(
            learning_type="memory",
            memory_records=({"memory_id": "corrupt"},),
        )
    )

    assert result.status == "blocked_learning"
    assert result.memory_safe is False
    assert "corrupt_memory_reuse_blocked" in result.reasons


def test_learning_safety_escalates_critical_security_to_centinela():
    safety = LearningSafety()

    result = safety.validate(
        LearningSafetyRequest(
            learning_type="security",
            security_status="critical",
            security_risk=True,
            centinela_status="blocked",
        )
    )

    assert result.status == "critical_learning"
    assert result.success is False
    assert result.centinela_escalation_required is True
    assert result.sentinel_escalation_required is True
    assert result.application_status == "escalation_required"
    assert "security_escalation_required" in result.reasons


def test_learning_safety_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    safety = LearningSafety(status=status)

    def broken_checks(*args, **kwargs):
        raise RuntimeError("learning safety exploded")

    monkeypatch.setattr(safety, "_checks", broken_checks)

    result = safety.validate(LearningSafetyRequest(learning_type="execution"))

    assert result.status == "error"
    assert result.success is False
    assert "learning_safety_error_contained" in result.reasons
    assert status.learning_safety_metrics()["learning_safety_errors"] == 1
