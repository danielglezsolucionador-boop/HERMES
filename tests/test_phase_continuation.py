from app.runner.execution_blocking import ExecutionBlockRequest, ExecutionBlocking
from app.runner.phase_continuation import (
    PhaseContinuation,
    PhaseContinuationRequest,
)
from app.services.runtime_status import RuntimeStatus


ROADMAP = (
    "5.3.5_EXECUTION_BLOCKING.md",
    "5.4.1_PHASE_CONTINUATION.md",
    "5.4.2_CHECKPOINT_RECOVERY.md",
)


def _ready_request(**overrides):
    values = {
        "current_phase": "5",
        "current_subphase": "5.4.1_PHASE_CONTINUATION.md",
        "roadmap": ROADMAP,
        "completed_subphases": (
            "5.3.5_EXECUTION_BLOCKING.md",
            "5.4.1_PHASE_CONTINUATION.md",
        ),
        "dependencies": {
            "5.4.2_CHECKPOINT_RECOVERY.md": (
                "5.4.1_PHASE_CONTINUATION.md",
            )
        },
        "governance_status": "approved",
        "audit_status": "approved",
        "execution_status": "completed",
        "runtime_state": {"status": "online", "loop_state": "active"},
        "execution_context": {"phase": "5.4.1"},
    }
    values.update(overrides)
    return PhaseContinuationRequest(**values)


def test_phase_continuation_detects_next_subphase_when_safe():
    status = RuntimeStatus()
    continuation = PhaseContinuation(status=status)

    result = continuation.evaluate(_ready_request())

    assert result.status == "ready"
    assert result.success is True
    assert result.current_subphase == "5.4.1_PHASE_CONTINUATION.md"
    assert result.next_subphase == "5.4.2_CHECKPOINT_RECOVERY.md"
    assert result.continuation_status == "ready_for_next_subphase"
    assert result.roadmap_loaded is True
    assert result.dependencies_satisfied is True
    assert result.governance_satisfied is True
    assert result.audit_satisfied is True
    assert result.execution_stable is True
    assert result.runtime_safe is True
    assert result.progression_allowed is True

    metrics = status.phase_continuation_metrics()
    assert metrics["phase_continuation_status"] == "ready"
    assert metrics["phase_continuations_ready"] == 1
    assert metrics["next_subphase"] == "5.4.2_CHECKPOINT_RECOVERY.md"


def test_phase_continuation_blocks_phase_skipping():
    continuation = PhaseContinuation()

    result = continuation.evaluate(
        _ready_request(next_subphase="5.4.3_EXECUTION_RESUME.md")
    )

    assert result.status == "blocked"
    assert result.success is False
    assert result.progression_allowed is False
    assert "phase_skipping_detected" in result.reasons


def test_phase_continuation_blocks_missing_dependencies():
    continuation = PhaseContinuation()

    result = continuation.evaluate(
        _ready_request(completed_subphases=("5.3.5_EXECUTION_BLOCKING.md",))
    )

    assert result.status == "blocked"
    assert result.dependencies_satisfied is False
    assert result.missing_dependencies == ("5.4.1_PHASE_CONTINUATION.md",)
    assert "missing_dependency:5.4.1_PHASE_CONTINUATION.md" in result.reasons


def test_phase_continuation_blocks_without_governance_audit_or_stability():
    continuation = PhaseContinuation()

    result = continuation.evaluate(
        _ready_request(
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


def test_phase_continuation_blocks_active_execution_block():
    execution_block = ExecutionBlocking().activate(
        ExecutionBlockRequest(
            execution_id="execution-1",
            block_type="human",
            block_reason="manual pause",
            risk_level="critical",
            human_requested=True,
        )
    )
    continuation = PhaseContinuation()

    result = continuation.evaluate(_ready_request(execution_blocking=execution_block))

    assert result.status == "blocked"
    assert result.runtime_safe is False
    assert "runtime_safety_required" in result.reasons


def test_phase_continuation_marks_completed_when_no_next_subphase():
    continuation = PhaseContinuation()

    result = continuation.evaluate(
        _ready_request(
            current_subphase="5.4.2_CHECKPOINT_RECOVERY.md",
            completed_subphases=ROADMAP,
            dependencies={},
        )
    )

    assert result.status == "completed"
    assert result.success is True
    assert result.next_subphase is None
    assert result.continuation_status == "roadmap_completed"
    assert result.progression_allowed is False


def test_phase_continuation_contains_internal_errors(monkeypatch):
    continuation = PhaseContinuation()

    def broken_next(*args, **kwargs):
        raise RuntimeError("roadmap lookup exploded")

    monkeypatch.setattr(continuation, "_next_subphase", broken_next)

    result = continuation.evaluate(_ready_request())

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_status == "blocked_phase_continuation_error"
    assert "phase_continuation_error_contained" in result.reasons
