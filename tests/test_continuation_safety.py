from app.runner.continuation_safety import (
    ContinuationSafety,
    ContinuationSafetyRequest,
)
from app.runner.workflow_chaining import WorkflowChaining, WorkflowChainingRequest
from app.services.runtime_status import RuntimeStatus


ROADMAP = (
    "5.4.4_WORKFLOW_CHAINING.md",
    "5.4.5_CONTINUATION_SAFETY.md",
)


def _workflow_chaining_result(**overrides):
    values = {
        "current_workflow": "5.4.4_WORKFLOW_CHAINING.md",
        "current_phase": "5",
        "current_subphase": "5.4.4_WORKFLOW_CHAINING.md",
        "roadmap": ROADMAP,
        "completed_workflows": ("5.4.4_WORKFLOW_CHAINING.md",),
        "dependencies": {
            "5.4.5_CONTINUATION_SAFETY.md": (
                "5.4.4_WORKFLOW_CHAINING.md",
            )
        },
        "governance_status": "approved",
        "audit_status": "approved",
        "execution_status": "completed",
        "runtime_state": {"status": "online", "loop_state": "active"},
    }
    values.update(overrides)
    return WorkflowChaining().chain(WorkflowChainingRequest(**values))


def _safety_request(**overrides):
    values = {
        "execution_id": "execution-1",
        "task_id": "task-1",
        "safety_type": "execution",
        "workflow_chaining": _workflow_chaining_result(),
        "runtime_state": {"status": "online", "loop_state": "active"},
        "execution_context": {"status": "completed"},
        "governance_history": ({"approval_status": "approved"},),
        "audit_history": ({"audit_status": "approved"},),
        "workflow_history": ({"workflow": "5.4.4_WORKFLOW_CHAINING.md"},),
        "continuation_logs": ({"event": "candidate_ready"},),
    }
    values.update(overrides)
    return ContinuationSafetyRequest(**values)


def test_continuation_safety_allows_safe_continuation_and_metrics():
    status = RuntimeStatus()
    safety = ContinuationSafety(status=status)

    result = safety.validate(_safety_request())

    assert result.status == "safe_continuation"
    assert result.success is True
    assert result.continuation_allowed is True
    assert result.human_review_required is False
    assert result.governance_valid is True
    assert result.audit_valid is True
    assert result.security_clear is True
    assert result.runtime_stable is True
    assert result.dependencies_complete is True
    assert result.execution_consistent is True
    assert result.workflow_integrity is True

    metrics = status.continuation_safety_metrics()
    assert metrics["continuation_safety_status"] == "safe_continuation"
    assert metrics["continuations_safe"] == 1
    assert metrics["continuation_allowed"] is True


def test_continuation_safety_allows_warning_with_visibility():
    safety = ContinuationSafety()

    result = safety.validate(
        _safety_request(
            audit_status="approved_with_warnings",
            risk_level="low",
            warnings=("provider latency elevated",),
        )
    )

    assert result.status == "warning_continuation"
    assert result.success is True
    assert result.continuation_allowed is True
    assert result.human_review_required is True
    assert result.autonomy_limited is True
    assert "warning_continuation_requires_visibility" in result.reasons


def test_continuation_safety_blocks_invalid_governance_audit_runtime_execution():
    safety = ContinuationSafety()

    result = safety.validate(
        _safety_request(
            workflow_chaining={
                "status": "activated",
                "dependencies_satisfied": False,
                "workflow_activation": True,
                "execution_status": "running",
            },
            governance_status="pending",
            audit_status="rejected",
            runtime_state={"status": "degraded"},
            dependency_status="blocked",
            execution_status="running",
        )
    )

    assert result.status == "blocked_continuation"
    assert result.continuation_allowed is False
    assert "governance_approval_required" in result.reasons
    assert "approved_audit_required" in result.reasons
    assert "runtime_stability_required" in result.reasons
    assert "dependency_completion_required" in result.reasons
    assert "execution_consistency_required" in result.reasons


def test_continuation_safety_escalates_critical_security_to_centinela():
    safety = ContinuationSafety()

    result = safety.validate(
        _safety_request(
            audit_response={
                "centinela_escalation": True,
                "security_escalation_status": "escalated_to_centinela",
                "risk_level": "critical",
            },
            detected_risks=("runtime compromise",),
            security_events=({"event": "security_block"},),
        )
    )

    assert result.status == "critical_continuation"
    assert result.success is False
    assert result.continuation_allowed is False
    assert result.sentinel_escalation_required is True
    assert result.centinela_escalation_required is True
    assert "critical_security_escalation_required" in result.reasons


def test_continuation_safety_respects_active_execution_block():
    safety = ContinuationSafety()

    result = safety.validate(
        _safety_request(
            execution_blocking={
                "status": "active",
                "continuation_blocked": True,
            }
        )
    )

    assert result.status == "blocked_continuation"
    assert result.execution_consistent is False
    assert "execution_consistency_required" in result.reasons


def test_continuation_safety_blocks_corrupt_workflow_chaining():
    safety = ContinuationSafety()

    result = safety.validate(
        _safety_request(
            workflow_chaining={
                "status": "blocked",
                "workflow_activation": False,
                "dependencies_satisfied": True,
                "governance_status": "approved",
                "audit_status": "approved",
                "execution_status": "completed",
            }
        )
    )

    assert result.status == "blocked_continuation"
    assert result.workflow_integrity is False
    assert "workflow_integrity_required" in result.reasons


def test_continuation_safety_contains_internal_errors(monkeypatch):
    safety = ContinuationSafety()

    def broken_security(*args, **kwargs):
        raise RuntimeError("security validation exploded")

    monkeypatch.setattr(safety, "_security_status", broken_security)

    result = safety.validate(_safety_request())

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_status == "blocked_error"
    assert "continuation_safety_error_contained" in result.reasons
