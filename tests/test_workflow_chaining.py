from app.runner.workflow_chaining import (
    WorkflowChaining,
    WorkflowChainingRequest,
)
from app.services.runtime_status import RuntimeStatus


ROADMAP = (
    "5.4.2_CHECKPOINT_RECOVERY.md",
    "5.4.3_EXECUTION_RESUME.md",
    "5.4.4_WORKFLOW_CHAINING.md",
    "5.4.5_CONTINUATION_SAFETY.md",
)


def _chain_request(**overrides):
    values = {
        "current_workflow": "5.4.4_WORKFLOW_CHAINING.md",
        "current_phase": "5",
        "current_subphase": "5.4.4_WORKFLOW_CHAINING.md",
        "chaining_type": "subphase",
        "roadmap": ROADMAP,
        "completed_workflows": (
            "5.4.2_CHECKPOINT_RECOVERY.md",
            "5.4.3_EXECUTION_RESUME.md",
            "5.4.4_WORKFLOW_CHAINING.md",
        ),
        "dependencies": {
            "5.4.5_CONTINUATION_SAFETY.md": (
                "5.4.4_WORKFLOW_CHAINING.md",
            )
        },
        "governance_status": "approved",
        "audit_status": "approved",
        "execution_status": "completed",
        "runtime_state": {"status": "online", "loop_state": "active"},
        "execution_context": {"status": "completed", "phase": "5.4.4"},
        "lifecycle_history": ({"state": "completed"},),
        "roadmap_history": ({"current": "5.4.4_WORKFLOW_CHAINING.md"},),
        "governance_history": ({"approval_status": "approved"},),
        "audit_history": ({"audit_status": "approved"},),
    }
    values.update(overrides)
    return WorkflowChainingRequest(**values)


def test_workflow_chaining_activates_next_workflow_and_metrics():
    status = RuntimeStatus()
    chaining = WorkflowChaining(status=status)

    result = chaining.chain(_chain_request())

    assert result.status == "activated"
    assert result.success is True
    assert result.next_workflow == "5.4.5_CONTINUATION_SAFETY.md"
    assert result.workflow_activation is True
    assert result.progression_allowed is True
    assert result.dependencies_satisfied is True
    assert result.governance_satisfied is True
    assert result.audit_satisfied is True
    assert result.execution_stable is True
    assert result.runtime_safe is True
    assert result.continuation_status == (
        "next_workflow_activated_under_chaining_control"
    )

    metrics = status.workflow_chaining_metrics()
    assert metrics["workflow_chaining_status"] == "activated"
    assert metrics["workflow_chains_activated"] == 1
    assert metrics["next_workflow"] == "5.4.5_CONTINUATION_SAFETY.md"
    assert metrics["workflow_activation"] is True


def test_workflow_chaining_blocks_workflow_skipping():
    chaining = WorkflowChaining()

    result = chaining.chain(
        _chain_request(next_workflow="5.5.1_OPERATIONAL_MEMORY.md")
    )

    assert result.status == "blocked"
    assert result.workflow_activation is False
    assert "workflow_skipping_detected" in result.reasons


def test_workflow_chaining_blocks_missing_dependencies():
    chaining = WorkflowChaining()

    result = chaining.chain(
        _chain_request(
            dependencies={
                "5.4.5_CONTINUATION_SAFETY.md": (
                    "5.4.4_WORKFLOW_CHAINING.md",
                    "external-governance-gate",
                )
            }
        )
    )

    assert result.status == "blocked"
    assert result.dependencies_satisfied is False
    assert "missing_dependency:external-governance-gate" in result.reasons


def test_workflow_chaining_blocks_without_governance_audit_or_stability():
    chaining = WorkflowChaining()

    result = chaining.chain(
        _chain_request(
            governance_status="pending",
            audit_status="rejected",
            execution_status="running",
            runtime_state={"status": "degraded"},
        )
    )

    assert result.status == "blocked"
    assert "governance_approval_required" in result.reasons
    assert "approved_audit_required" in result.reasons
    assert "stable_execution_required" in result.reasons
    assert "runtime_safety_required" in result.reasons


def test_workflow_chaining_marks_roadmap_completed_without_next_workflow():
    chaining = WorkflowChaining()

    result = chaining.chain(
        _chain_request(
            current_workflow="5.4.5_CONTINUATION_SAFETY.md",
            current_subphase="5.4.5_CONTINUATION_SAFETY.md",
            completed_workflows=ROADMAP,
            dependencies={},
        )
    )

    assert result.status == "completed"
    assert result.success is True
    assert result.next_workflow is None
    assert result.workflow_activation is False
    assert result.continuation_status == "roadmap_completed"


def test_workflow_chaining_blocks_unfinished_terminal_workflow():
    chaining = WorkflowChaining()

    result = chaining.chain(
        _chain_request(
            current_workflow="5.4.5_CONTINUATION_SAFETY.md",
            current_subphase="5.4.5_CONTINUATION_SAFETY.md",
            completed_workflows=(
                "5.4.2_CHECKPOINT_RECOVERY.md",
                "5.4.3_EXECUTION_RESUME.md",
            ),
            dependencies={},
        )
    )

    assert result.status == "blocked"
    assert "current_workflow_completion_required" in result.reasons


def test_workflow_chaining_contains_internal_errors(monkeypatch):
    chaining = WorkflowChaining()

    def broken_next(*args, **kwargs):
        raise RuntimeError("workflow lookup exploded")

    monkeypatch.setattr(chaining, "_next_workflow", broken_next)

    result = chaining.chain(_chain_request())

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_status == "blocked_workflow_chaining_error"
    assert "workflow_chaining_error_contained" in result.reasons
