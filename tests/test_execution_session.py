from app.runner.execution_session import (
    SESSION_STATE_COMPLETED,
    SESSION_STATE_FAILED,
    SESSION_STATE_RUNNING,
    SESSION_STATE_WAITING,
    ExecutionSessionManager,
)


def make_manager() -> ExecutionSessionManager:
    return ExecutionSessionManager(
        runtime_owner="runner-test:runtime-test",
        max_active_sessions=1,
        max_log_entries=5,
    )


def test_execution_session_starts_with_task_phase_and_context():
    manager = make_manager()

    result = manager.start_session(
        {"id": "task-1", "title": "Test task", "phase_id": "5.1.1"},
        runtime_context={"runtime": "active"},
        context_memory={"checkpoint": "created"},
        audit_status="pending",
    )

    assert result.status == "started"
    assert result.success is True
    assert result.session_state == SESSION_STATE_RUNNING
    assert result.task_id == "task-1"
    assert result.phase_id == "5.1.1"
    assert result.active_sessions == 1
    assert result.recovery_available is True
    assert result.session is not None
    assert result.session.context_memory["checkpoint"] == "created"
    assert result.session.runtime_context["runtime"] == "active"
    assert result.session.audit_status == "pending"
    assert result.session.logs[-1].event == "session_started"


def test_execution_session_rejects_conflicting_active_session():
    manager = make_manager()
    manager.start_session({"id": "task-1", "phase_id": "5.1.1"})

    result = manager.start_session({"id": "task-2", "phase_id": "5.1.1"})

    assert result.status == "rejected"
    assert result.success is False
    assert "conflicting_execution_session_active" in result.reasons
    assert result.active_sessions == 1


def test_execution_session_save_preserves_progress_and_memory():
    manager = make_manager()
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.1"})

    result = manager.save_session(
        started.session_id,
        checkpoint="loaded-context",
        file_modified="app/runner/example.py",
        result="context_loaded",
        audit_status="waiting_audit",
        last_audit="audit-created",
        context_updates={"loaded": True},
        state=SESSION_STATE_WAITING,
    )

    assert result.status == "saved"
    assert result.success is True
    assert result.session_state == SESSION_STATE_WAITING
    assert result.last_checkpoint == "loaded-context"
    assert result.last_file_modified == "app/runner/example.py"
    assert result.last_result == "context_loaded"
    assert result.audit_status == "waiting_audit"
    assert result.last_audit == "audit-created"
    assert result.session is not None
    assert result.session.context_memory["loaded"] is True
    assert result.session.logs[-1].event == "session_saved"


def test_execution_session_recover_restores_running_state():
    manager = make_manager()
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.1"})
    manager.save_session(
        started.session_id,
        checkpoint="checkpoint-1",
        state=SESSION_STATE_WAITING,
    )

    result = manager.recover_session(session_id=started.session_id)

    assert result.status == "recovered"
    assert result.success is True
    assert result.session_state == SESSION_STATE_RUNNING
    assert result.session_id == started.session_id
    assert result.last_checkpoint == "checkpoint-1"
    assert result.active_sessions == 1
    assert result.session is not None
    assert result.session.logs[-1].event == "session_recovered"


def test_execution_session_close_completed_releases_active_session():
    manager = make_manager()
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.1"})

    result = manager.close_session(started.session_id, result="done")

    assert result.status == "closed"
    assert result.success is True
    assert result.session_state == SESSION_STATE_COMPLETED
    assert result.last_result == "done"
    assert result.recovery_available is False
    assert result.active_sessions == 0
    assert manager.visibility()["active_sessions"] == 0


def test_execution_session_close_failed_preserves_error():
    manager = make_manager()
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.1"})

    result = manager.close_session(
        started.session_id,
        completed=False,
        error="provider_unavailable",
    )

    assert result.status == "closed"
    assert result.success is False
    assert result.session_state == SESSION_STATE_FAILED
    assert result.last_error == "provider_unavailable"
    assert result.recovery_available is False
    assert result.active_sessions == 0


def test_execution_session_rejects_missing_task_id():
    manager = make_manager()

    result = manager.start_session({"title": "Missing id"}, phase_id="5.1.1")

    assert result.status == "rejected"
    assert result.success is False
    assert "missing_task_id" in result.reasons
    assert result.active_sessions == 0
