from app.runner.checkpoint_recovery import (
    CheckpointRecovery,
    CheckpointRequest,
    RecoveryRequest,
)
from app.services.runtime_status import RuntimeStatus


def _checkpoint_request(**overrides):
    values = {
        "execution_id": "execution-1",
        "task_id": "task-1",
        "checkpoint_type": "execution",
        "phase_state": {
            "current_phase": "5",
            "current_subphase": "5.4.2_CHECKPOINT_RECOVERY.md",
        },
        "runtime_state": {"status": "online", "loop_state": "active"},
        "governance_state": {"approval_status": "approved"},
        "audit_state": {"audit_status": "approved"},
        "provider_state": {"provider": "openrouter", "status": "idle"},
        "execution_context": {"status": "completed"},
        "lifecycle_state": {"stage": "checkpoint"},
        "modified_files": ("app/runner/checkpoint_recovery.py",),
        "recovery_logs": ({"event": "before_continuation"},),
    }
    values.update(overrides)
    return CheckpointRequest(**values)


def test_checkpoint_recovery_creates_integrity_checked_checkpoint():
    status = RuntimeStatus()
    recovery = CheckpointRecovery(status=status)

    result = recovery.create(_checkpoint_request())

    assert result.status == "created"
    assert result.success is True
    assert result.checkpoint_id
    assert result.checkpoint_valid is True
    assert result.checkpoint_checksum
    assert result.continuation_status == "checkpoint_saved_no_auto_continue"
    assert result.context_preserved is True
    assert result.traceability_preserved is True
    assert result.checkpoint["state"]["execution_context"]["status"] == "completed"

    metrics = status.checkpoint_recovery_metrics()
    assert metrics["checkpoint_recovery_status"] == "created"
    assert metrics["checkpoints_created"] == 1
    assert metrics["checkpoint_valid"] is True


def test_checkpoint_recovery_blocks_invalid_checkpoint_creation():
    recovery = CheckpointRecovery()

    result = recovery.create(CheckpointRequest(execution_id="execution-1"))

    assert result.status == "blocked"
    assert result.success is False
    assert result.checkpoint_valid is False
    assert "missing_checkpoint_state" in result.reasons


def test_checkpoint_recovery_prepares_restoration_from_valid_checkpoint():
    recovery = CheckpointRecovery()
    checkpoint = recovery.create(_checkpoint_request()).checkpoint

    result = recovery.recover(
        RecoveryRequest(
            execution_id="execution-1",
            checkpoints=(checkpoint,),
            current_logs=({"event": "provider_failure"},),
        )
    )

    assert result.status == "recovery_prepared"
    assert result.success is True
    assert result.restoration_ready is True
    assert result.checkpoint_valid is True
    assert result.continuation_status == "blocked_pending_recovery_validation"
    assert result.restored_state["execution_context"]["status"] == "completed"
    assert "continuation_blocked_until_recovery_validation" in result.reasons


def test_checkpoint_recovery_blocks_tampered_checkpoint():
    recovery = CheckpointRecovery()
    checkpoint = recovery.create(_checkpoint_request()).checkpoint
    checkpoint["state"]["execution_context"]["status"] = "tampered"

    result = recovery.recover(
        RecoveryRequest(execution_id="execution-1", checkpoints=(checkpoint,))
    )

    assert result.status == "blocked"
    assert result.success is False
    assert result.checkpoint_valid is False
    assert "valid_checkpoint_not_found" in result.reasons


def test_checkpoint_recovery_requires_review_for_critical_state():
    recovery = CheckpointRecovery()

    result = recovery.create(
        _checkpoint_request(
            checkpoint_type="runtime",
            modified_files=("app/runner/runtime_loop.py",),
            runtime_state={"status": "online", "component": "runtime_loop"},
        )
    )

    assert result.status == "created"
    assert result.governance_review_required is True
    assert result.audit_review_required is True


def test_checkpoint_recovery_blocks_missing_checkpoint_match():
    recovery = CheckpointRecovery()
    checkpoint = recovery.create(_checkpoint_request()).checkpoint

    result = recovery.recover(
        RecoveryRequest(execution_id="other-execution", checkpoints=(checkpoint,))
    )

    assert result.status == "blocked"
    assert result.success is False
    assert "matching_checkpoint_not_found" in result.reasons


def test_checkpoint_recovery_contains_internal_errors(monkeypatch):
    recovery = CheckpointRecovery()

    def broken_record(*args, **kwargs):
        raise RuntimeError("checkpoint exploded")

    monkeypatch.setattr(recovery, "_checkpoint_record", broken_record)

    result = recovery.create(_checkpoint_request())

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_status == "blocked_checkpoint_error"
    assert "checkpoint_recovery_error_contained" in result.reasons
