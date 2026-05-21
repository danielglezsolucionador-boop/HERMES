from app.runner.execution_context_memory import ExecutionContextMemory
from app.runner.execution_session import ExecutionSessionManager


def _session_dict() -> dict:
    return {
        "session_id": "session-1",
        "phase_id": "5.1.4",
        "task_id": "task-1",
        "execution_status": "running",
        "lifecycle_stage": "active_execution",
        "audit_status": "not_started",
    }


def test_context_memory_preserves_required_components():
    memory = ExecutionContextMemory()

    result = memory.preserve(
        _session_dict(),
        checkpoint="before-audit",
        last_action="validate",
        modified_files=["app/runner/example.py"],
        audit_status="pending",
        human_approval_status="waiting",
        provider_context={"provider": "openrouter"},
    )

    assert result.status == "preserved"
    assert result.success is True
    assert result.recovery_available is True
    assert result.snapshot is not None
    assert result.snapshot.execution_id == "session-1"
    assert result.snapshot.phase_id == "5.1.4"
    assert result.snapshot.task_id == "task-1"
    assert result.snapshot.last_checkpoint == "before-audit"
    assert result.snapshot.last_action == "validate"
    assert result.snapshot.modified_files == ("app/runner/example.py",)
    assert result.snapshot.provider_context["provider"] == "openrouter"


def test_context_memory_rejects_corrupt_context():
    memory = ExecutionContextMemory()

    result = memory.preserve(
        {
            "session_id": "",
            "phase_id": "5.1.4",
            "task_id": "task-1",
            "execution_status": "running",
        }
    )

    assert result.status == "rejected"
    assert result.success is False
    assert "missing_execution_id" in result.reasons


def test_context_memory_recovers_matching_checkpoint():
    memory = ExecutionContextMemory()
    preserved = memory.preserve(
        _session_dict(),
        checkpoint="safe-point",
        last_action="before-critical-change",
    )

    result = memory.recover(
        [preserved.snapshot.to_dict()],
        task_id="task-1",
        phase_id="5.1.4",
    )

    assert result.status == "recovered"
    assert result.success is True
    assert result.snapshot is not None
    assert result.snapshot.last_checkpoint == "safe-point"


def test_session_save_preserves_context_snapshot_and_files():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.4"})

    result = manager.save_session(
        started.session_id,
        checkpoint="before-audit",
        file_modified="app/runner/execution_session.py",
        last_action="saved-progress",
        human_approval_status="waiting",
        provider_context={"provider": "openrouter", "model": "test-model"},
    )

    assert result.status == "saved"
    assert result.context_recovery_available is True
    assert result.last_checkpoint == "before-audit"
    assert result.last_action == "saved-progress"
    assert result.human_approval_status == "waiting"
    assert result.modified_files == ("app/runner/execution_session.py",)
    assert result.context_snapshot is not None
    assert result.context_snapshot["provider_context"]["provider"] == "openrouter"
    assert result.session is not None
    assert len(result.session.context_snapshots) == 2


def test_session_recovery_requires_valid_context_snapshot():
    manager = ExecutionSessionManager(runtime_owner="runner-test:runtime-test")
    started = manager.start_session({"id": "task-1", "phase_id": "5.1.4"})
    manager.save_session(
        started.session_id,
        checkpoint="safe-point",
        last_action="ready-to-recover",
    )

    result = manager.recover_session(session_id=started.session_id)

    assert result.status == "recovered"
    assert result.context_recovery_available is True
    assert result.context_snapshot is not None
    assert result.context_snapshot["last_checkpoint"] == "safe-point"
