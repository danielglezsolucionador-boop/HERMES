from copy import deepcopy

from app.runner.checkpoint_recovery import (
    CheckpointRecovery,
    CheckpointRequest,
    RecoveryRequest,
)
from app.runner.execution_resume import ExecutionResume, ExecutionResumeRequest
from app.services.runtime_status import RuntimeStatus


def _checkpoint_recovery_result(**overrides):
    values = {
        "execution_id": "execution-1",
        "task_id": "task-1",
        "checkpoint_type": "execution",
        "phase_state": {
            "current_phase": "5",
            "current_subphase": "5.4.3_EXECUTION_RESUME.md",
        },
        "runtime_state": {"status": "online", "loop_state": "active"},
        "governance_state": {"approval_status": "approved"},
        "audit_state": {"audit_status": "approved"},
        "provider_state": {"provider": "openrouter", "status": "idle"},
        "execution_context": {
            "execution_id": "execution-1",
            "task_id": "task-1",
            "status": "paused",
        },
        "lifecycle_state": {"stage": "paused"},
        "modified_files": ("app/runner/execution_resume.py",),
        "recovery_logs": ({"event": "checkpoint_ready"},),
    }
    values.update(overrides)
    recovery = CheckpointRecovery()
    checkpoint = recovery.create(CheckpointRequest(**values)).checkpoint
    return recovery.recover(
        RecoveryRequest(
            execution_id="execution-1",
            checkpoints=(checkpoint,),
            current_logs=({"event": "runtime_interrupted"},),
        )
    )


def _resume_request(**overrides):
    values = {
        "execution_id": "execution-1",
        "task_id": "task-1",
        "resume_type": "recovery",
        "paused_execution": {"execution_id": "execution-1", "state": "paused"},
        "checkpoint_recovery": _checkpoint_recovery_result(),
        "lifecycle_history": ({"state": "paused"},),
        "audit_history": ({"audit_status": "approved"},),
        "governance_history": ({"approval_status": "approved"},),
        "recovery_history": ({"recovery_status": "restoration_prepared"},),
        "modified_files": ("app/runner/execution_resume.py",),
    }
    values.update(overrides)
    return ExecutionResumeRequest(**values)


def test_execution_resume_reactivates_recovered_execution_and_metrics():
    status = RuntimeStatus()
    resume = ExecutionResume(status=status)

    result = resume.resume(_resume_request())

    assert result.status == "resumed"
    assert result.success is True
    assert result.execution_reactivated is True
    assert result.checkpoint_valid is True
    assert result.runtime_stable is True
    assert result.governance_satisfied is True
    assert result.audit_satisfied is True
    assert result.workflow_continuity_preserved is True
    assert result.continuation_status == "workflow_reactivated_under_resume_control"
    assert result.restored_state["execution_status"] == "resumed"

    metrics = status.execution_resume_metrics()
    assert metrics["execution_resume_status"] == "resumed"
    assert metrics["execution_resumes_completed"] == 1
    assert metrics["execution_reactivated"] is True
    assert metrics["checkpoint_valid"] is True


def test_execution_resume_blocks_tampered_checkpoint():
    recovery_result = _checkpoint_recovery_result()
    checkpoint = deepcopy(recovery_result.checkpoint)
    checkpoint["state"]["execution_context"]["status"] = "tampered"
    resume = ExecutionResume()

    result = resume.resume(
        _resume_request(
            checkpoint_recovery=recovery_result,
            checkpoint=checkpoint,
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert result.checkpoint_valid is False
    assert "valid_checkpoint_required" in result.reasons


def test_execution_resume_blocks_without_governance_or_audit():
    resume = ExecutionResume()

    result = resume.resume(
        _resume_request(
            governance_state={"approval_status": "pending"},
            audit_state={"audit_status": "rejected"},
        )
    )

    assert result.status == "blocked"
    assert result.governance_satisfied is False
    assert result.audit_satisfied is False
    assert "governance_approval_required" in result.reasons
    assert "approved_audit_required" in result.reasons


def test_execution_resume_blocks_duplicate_active_execution():
    resume = ExecutionResume()

    result = resume.resume(
        _resume_request(
            active_executions=(
                {"execution_id": "execution-1", "status": "executing"},
            )
        )
    )

    assert result.status == "blocked"
    assert result.execution_reactivated is False
    assert "duplicate_execution_detected" in result.reasons


def test_execution_resume_allows_manual_resume_without_checkpoint():
    resume = ExecutionResume()

    result = resume.resume(
        ExecutionResumeRequest(
            execution_id="execution-1",
            task_id="task-1",
            resume_type="manual",
            paused_execution={"execution_id": "execution-1", "state": "paused"},
            runtime_state={"status": "online"},
            governance_state={"approval_status": "approved"},
            audit_state={"audit_status": "approved"},
            provider_state={"provider": "openrouter", "status": "idle"},
            execution_context={
                "execution_id": "execution-1",
                "task_id": "task-1",
                "status": "paused",
            },
            lifecycle_state={"stage": "paused"},
        )
    )

    assert result.status == "resumed"
    assert result.resume_type == "manual"
    assert result.checkpoint_valid is False
    assert result.execution_reactivated is True


def test_execution_resume_blocks_completed_execution():
    resume = ExecutionResume()

    result = resume.resume(
        _resume_request(
            paused_execution={"execution_id": "execution-1", "state": "completed"},
            execution_context={
                "execution_id": "execution-1",
                "task_id": "task-1",
                "status": "completed",
            },
            lifecycle_state={"stage": "completed"},
        )
    )

    assert result.status == "blocked"
    assert result.workflow_continuity_preserved is False
    assert "workflow_continuity_required" in result.reasons


def test_execution_resume_contains_internal_errors(monkeypatch):
    resume = ExecutionResume()

    def broken_restore(*args, **kwargs):
        raise RuntimeError("resume context exploded")

    monkeypatch.setattr(resume, "_restored_state", broken_restore)

    result = resume.resume(_resume_request())

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_status == "blocked_execution_resume_error"
    assert "execution_resume_error_contained" in result.reasons
