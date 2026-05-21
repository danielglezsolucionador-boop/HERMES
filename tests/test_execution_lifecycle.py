from app.runner.execution_lifecycle import (
    APPROVAL_APPROVED,
    AUDIT_APPROVED,
    AUDIT_REJECTED,
    LIFECYCLE_STAGE_ACTIVE_EXECUTION,
    LIFECYCLE_STAGE_AUDIT_REQUEST,
    LIFECYCLE_STAGE_AUDIT_RESULT,
    LIFECYCLE_STAGE_CONTINUATION_DECISION,
    LIFECYCLE_STAGE_EXECUTION_CLOSE,
    LIFECYCLE_STAGE_HUMAN_APPROVAL,
    LIFECYCLE_STAGE_SELF_VALIDATION,
    LIFECYCLE_STAGE_TASK_RECEPTION,
    ExecutionLifecycleController,
)
from app.runner.execution_session import ExecutionSessionManager


def test_lifecycle_bootstrap_starts_at_task_reception():
    controller = ExecutionLifecycleController()

    history = controller.bootstrap_history()

    assert history[0]["next_stage"] == LIFECYCLE_STAGE_TASK_RECEPTION
    assert history[-1]["next_stage"] == LIFECYCLE_STAGE_ACTIVE_EXECUTION
    assert all(item["allowed"] is True for item in history)


def test_lifecycle_blocks_audit_without_self_validation():
    controller = ExecutionLifecycleController()

    result = controller.evaluate_transition(
        LIFECYCLE_STAGE_SELF_VALIDATION,
        LIFECYCLE_STAGE_AUDIT_REQUEST,
    )

    assert result.allowed is False
    assert "self_validation_required_before_audit" in result.reasons


def test_lifecycle_allows_audit_after_self_validation():
    controller = ExecutionLifecycleController()

    result = controller.evaluate_transition(
        LIFECYCLE_STAGE_SELF_VALIDATION,
        LIFECYCLE_STAGE_AUDIT_REQUEST,
        validation_passed=True,
    )

    assert result.allowed is True
    assert result.lifecycle_transition == "self_validation->audit_request"


def test_lifecycle_blocks_rejected_audit_from_human_approval():
    controller = ExecutionLifecycleController()

    result = controller.evaluate_transition(
        LIFECYCLE_STAGE_AUDIT_RESULT,
        LIFECYCLE_STAGE_HUMAN_APPROVAL,
        audit_status=AUDIT_REJECTED,
    )

    assert result.allowed is False
    assert "audit_approval_required_before_human_approval" in result.reasons


def test_lifecycle_requires_human_authorization_for_continuation():
    controller = ExecutionLifecycleController()

    blocked = controller.evaluate_transition(
        LIFECYCLE_STAGE_CONTINUATION_DECISION,
        LIFECYCLE_STAGE_ACTIVE_EXECUTION,
    )
    allowed = controller.evaluate_transition(
        LIFECYCLE_STAGE_CONTINUATION_DECISION,
        LIFECYCLE_STAGE_ACTIVE_EXECUTION,
        human_authorized=True,
    )

    assert blocked.allowed is False
    assert "human_authorization_required_for_continuation" in blocked.reasons
    assert allowed.allowed is True


def test_lifecycle_requires_explicit_close_request():
    controller = ExecutionLifecycleController()

    blocked = controller.evaluate_transition(
        LIFECYCLE_STAGE_CONTINUATION_DECISION,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
    )
    allowed = controller.evaluate_transition(
        LIFECYCLE_STAGE_CONTINUATION_DECISION,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
        close_requested=True,
    )

    assert blocked.allowed is False
    assert "explicit_close_request_required" in blocked.reasons
    assert allowed.allowed is True


def test_session_lifecycle_advances_with_required_gates():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.3"})

    validation = manager.advance_lifecycle(
        started.session_id,
        LIFECYCLE_STAGE_SELF_VALIDATION,
    )
    audit_request = manager.advance_lifecycle(
        started.session_id,
        LIFECYCLE_STAGE_AUDIT_REQUEST,
        validation_passed=True,
    )
    audit_result = manager.advance_lifecycle(
        started.session_id,
        LIFECYCLE_STAGE_AUDIT_RESULT,
        audit_status=AUDIT_APPROVED,
    )
    human = manager.advance_lifecycle(
        started.session_id,
        LIFECYCLE_STAGE_HUMAN_APPROVAL,
        audit_status=AUDIT_APPROVED,
    )
    decision = manager.advance_lifecycle(
        started.session_id,
        LIFECYCLE_STAGE_CONTINUATION_DECISION,
        approval_status=APPROVAL_APPROVED,
    )
    closed = manager.advance_lifecycle(
        started.session_id,
        LIFECYCLE_STAGE_EXECUTION_CLOSE,
        close_requested=True,
    )

    assert validation.status == "lifecycle_advanced"
    assert audit_request.lifecycle_transition == "self_validation->audit_request"
    assert audit_result.lifecycle_stage == LIFECYCLE_STAGE_AUDIT_RESULT
    assert human.lifecycle_stage == LIFECYCLE_STAGE_HUMAN_APPROVAL
    assert decision.lifecycle_stage == LIFECYCLE_STAGE_CONTINUATION_DECISION
    assert closed.lifecycle_stage == LIFECYCLE_STAGE_EXECUTION_CLOSE
    assert closed.session is not None
    assert len(closed.session.lifecycle_history) >= 9


def test_session_lifecycle_blocks_skipping_audit():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.3"})

    result = manager.advance_lifecycle(
        started.session_id,
        LIFECYCLE_STAGE_HUMAN_APPROVAL,
        audit_status=AUDIT_APPROVED,
    )

    assert result.status == "rejected"
    assert result.lifecycle_transition_allowed is False
    assert "invalid_lifecycle_transition" in result.reasons
