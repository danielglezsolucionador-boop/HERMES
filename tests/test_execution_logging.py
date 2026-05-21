from app.runner.execution_session import ExecutionSessionManager


def test_execution_log_entry_contains_required_components():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")

    result = manager.start_session({"id": "task-1", "phase_id": "5.1.5"})

    assert result.session is not None
    log = result.session.logs[-1].to_dict()
    assert log["log_id"]
    assert log["execution_id"] == result.session_id
    assert log["phase_id"] == "5.1.5"
    assert log["created_at"]
    assert log["event_type"] == "execution"
    assert log["runtime_state"] == "running"
    assert log["actor"] == "hermes_runtime"
    assert log["severity"] == "info"
    assert isinstance(log["details"], dict)


def test_execution_logging_records_action_error_audit_approval_and_security():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.5"})

    manager.record_log(
        started.session_id,
        "action",
        details={"file": "app/runner/example.py"},
        message="File updated.",
    )
    manager.record_log(
        started.session_id,
        "error",
        details={"reason": "provider_failure"},
        severity="error",
    )
    manager.record_log(
        started.session_id,
        "audit",
        details={"status": "requested"},
    )
    manager.record_log(
        started.session_id,
        "approval",
        details={"status": "waiting"},
    )
    result = manager.record_log(
        started.session_id,
        "security",
        details={"reason": "invalid_transition"},
        severity="warning",
    )

    assert result.status == "log_recorded"
    assert result.session is not None
    event_types = {entry.event_type for entry in result.session.logs}
    assert {"action", "error", "audit", "approval", "security"}.issubset(
        event_types
    )
    assert result.last_log is not None
    assert result.last_log["event_type"] == "security"


def test_execution_logging_preserves_critical_logs_when_trimming():
    manager = ExecutionSessionManager(
        runtime_owner="runner-test:runtime-test",
        max_log_entries=3,
    )
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.5"})

    manager.record_log(started.session_id, "action", details={"step": 1})
    manager.record_log(
        started.session_id,
        "error",
        details={"reason": "critical-provider-failure"},
        severity="error",
    )
    manager.record_log(started.session_id, "action", details={"step": 2})
    result = manager.record_log(started.session_id, "action", details={"step": 3})

    assert result.session is not None
    assert len(result.session.logs) == 3
    assert any(entry.event_type == "error" for entry in result.session.logs)


def test_execution_logging_rejects_missing_session():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")

    result = manager.record_log("missing-session", "error")

    assert result.status == "rejected"
    assert result.success is False
    assert "missing_execution_session" in result.reasons
