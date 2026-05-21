from app.runner.execution_session import (
    SESSION_STATE_BLOCKED,
    SESSION_STATE_COMPLETED,
    SESSION_STATE_FAILED,
    SESSION_STATE_RUNNING,
    SESSION_STATE_WAITING_AUDIT,
    ExecutionSessionManager,
)
from app.runner.execution_state_control import (
    EXECUTION_STATE_CREATED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INITIALIZING,
    EXECUTION_STATE_RUNNING,
    ExecutionStateController,
)


def test_execution_state_controller_allows_defined_lifecycle_transitions():
    controller = ExecutionStateController()

    initializing = controller.evaluate_transition(
        EXECUTION_STATE_CREATED,
        EXECUTION_STATE_INITIALIZING,
    )
    running = controller.evaluate_transition(
        EXECUTION_STATE_INITIALIZING,
        EXECUTION_STATE_RUNNING,
    )

    assert initializing.allowed is True
    assert initializing.transition == "created->initializing"
    assert running.allowed is True
    assert running.transition == "initializing->running"


def test_execution_state_controller_blocks_skipped_transition():
    controller = ExecutionStateController()

    result = controller.evaluate_transition(
        EXECUTION_STATE_CREATED,
        EXECUTION_STATE_RUNNING,
    )

    assert result.allowed is False
    assert result.status == "rejected"
    assert "invalid_execution_state_transition" in result.reasons


def test_execution_state_controller_blocks_dangerous_terminal_transitions():
    controller = ExecutionStateController()

    failed_to_completed = controller.evaluate_transition(
        SESSION_STATE_FAILED,
        SESSION_STATE_COMPLETED,
    )
    completed_to_running = controller.evaluate_transition(
        SESSION_STATE_COMPLETED,
        SESSION_STATE_RUNNING,
    )

    assert failed_to_completed.allowed is False
    assert "failed_cannot_transition_to_completed" in failed_to_completed.reasons
    assert completed_to_running.allowed is False
    assert "completed_state_is_terminal" in completed_to_running.reasons


def test_execution_state_controller_requires_authorized_recovery():
    controller = ExecutionStateController()

    blocked = controller.evaluate_transition(
        EXECUTION_STATE_FAILED,
        EXECUTION_STATE_RUNNING,
    )
    recovered = controller.evaluate_transition(
        EXECUTION_STATE_FAILED,
        EXECUTION_STATE_RUNNING,
        recovery_authorized=True,
    )

    assert blocked.allowed is False
    assert "failed_requires_recovery_authorization" in blocked.reasons
    assert recovered.allowed is True
    assert "recovery_authorized" in recovered.reasons


def test_execution_state_controller_detects_operational_blocks():
    controller = ExecutionStateController()

    result = controller.evaluate_transition(
        SESSION_STATE_RUNNING,
        SESSION_STATE_BLOCKED,
        reasons=["provider_failure"],
        metadata={"runtime_corruption": True},
    )

    assert result.allowed is True
    assert result.blocking_detected is True
    assert "provider_failure" in result.blocking_reasons
    assert "runtime_corruption" in result.blocking_reasons


def test_execution_session_records_bootstrap_state_history():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")

    result = manager.start_session({"id": "task-1", "phase_id": "5.1.2"})

    assert result.status == "started"
    assert result.state_transition == "initializing->running"
    assert result.session is not None
    assert [item["transition"] for item in result.session.state_history] == [
        "created->initializing",
        "initializing->running",
    ]


def test_execution_session_blocks_invalid_completed_to_running_transition():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.2"})
    closed = manager.close_session(started.session_id)

    result = manager.save_session(
        closed.session_id,
        state=SESSION_STATE_RUNNING,
        recovery_authorized=True,
    )

    assert result.status == "rejected"
    assert result.state_transition_allowed is False
    assert "cannot_update_closed_session" in result.reasons


def test_execution_session_transitions_waiting_audit_back_to_running():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.2"})

    waiting = manager.save_session(
        started.session_id,
        state=SESSION_STATE_WAITING_AUDIT,
        transition_reasons=["audit_required"],
    )
    running = manager.save_session(
        started.session_id,
        state=SESSION_STATE_RUNNING,
        transition_reasons=["audit_accepted"],
    )

    assert waiting.status == "saved"
    assert waiting.session_state == SESSION_STATE_WAITING_AUDIT
    assert waiting.state_transition == "running->waiting_audit"
    assert running.status == "saved"
    assert running.session_state == SESSION_STATE_RUNNING
    assert running.state_transition == "waiting_audit->running"
