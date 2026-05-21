from app.runner.operational_memory import (
    OperationalMemory,
    OperationalMemoryCaptureRequest,
    OperationalMemoryQuery,
)
from app.services.runtime_status import RuntimeStatus


def _capture_request(**overrides):
    values = {
        "execution_id": "execution-1",
        "task_id": "task-1",
        "memory_type": "execution",
        "workflow": "5.5.1_OPERATIONAL_MEMORY.md",
        "event_type": "workflow_completed",
        "memory_context": {
            "execution_id": "execution-1",
            "summary": "operational memory captured",
        },
        "outputs": {"tests": "passed"},
        "governance_status": "approved",
        "audit_status": "approved",
        "risk_level": "clear",
        "governance_history": ({"approval_status": "approved"},),
        "audit_history": ({"audit_status": "approved"},),
        "workflow_history": ({"workflow": "5.5.1_OPERATIONAL_MEMORY.md"},),
        "continuation_history": ({"continuation_status": "safe"},),
    }
    values.update(overrides)
    return OperationalMemoryCaptureRequest(**values)


def test_operational_memory_captures_execution_memory_and_metrics():
    status = RuntimeStatus()
    memory = OperationalMemory(status=status)

    result = memory.capture(_capture_request())

    assert result.status == "captured"
    assert result.success is True
    assert result.memory_id
    assert result.integrity_valid is True
    assert result.context_safe is True
    assert result.governance_safe is True
    assert result.traceability_preserved is True
    assert result.memory_record["execution_id"] == "execution-1"

    metrics = status.operational_memory_metrics()
    assert metrics["operational_memory_status"] == "captured"
    assert metrics["memories_captured"] == 1
    assert metrics["integrity_valid"] is True


def test_operational_memory_retrieves_matching_memory_for_reuse():
    memory = OperationalMemory()
    captured = memory.capture(_capture_request())

    result = memory.retrieve(
        OperationalMemoryQuery(
            execution_id="execution-1",
            memory_type="execution",
            workflow="5.5.1_OPERATIONAL_MEMORY.md",
            query_context={"use_for_context": True},
        )
    )

    assert result.status == "retrieved"
    assert result.success is True
    assert result.reuse_allowed is True
    assert result.matched_records == 1
    assert result.memory_id == captured.memory_id
    assert result.reusable_context["records"][0]["memory_id"] == captured.memory_id


def test_operational_memory_blocks_incompatible_context_capture():
    memory = OperationalMemory()

    result = memory.capture(
        _capture_request(memory_context={"execution_id": "other-execution"})
    )

    assert result.status == "blocked"
    assert result.context_safe is False
    assert "context_incompatible" in result.reasons


def test_operational_memory_blocks_corrupt_memory_retrieval():
    memory = OperationalMemory()

    result = memory.retrieve(
        OperationalMemoryQuery(
            execution_id="execution-1",
            memory_records=(
                {
                    "memory_id": "bad-record",
                    "execution_id": "execution-1",
                    "memory_type": "execution",
                },
            ),
        )
    )

    assert result.status == "blocked"
    assert result.integrity_valid is False
    assert result.corrupt_records == 1
    assert "memory_corruption_detected" in result.reasons


def test_operational_memory_blocks_reuse_that_would_bypass_governance():
    memory = OperationalMemory()
    memory.capture(
        _capture_request(
            memory_type="governance",
            governance_status="rejected",
            memory_context={"execution_id": "execution-1", "decision": "rejected"},
        )
    )

    result = memory.retrieve(
        OperationalMemoryQuery(
            execution_id="execution-1",
            memory_type="governance",
            query_context={"use_for_continuation": True},
        )
    )

    assert result.status == "blocked"
    assert result.governance_safe is False
    assert "governance_memory_blocks_reuse" in result.reasons


def test_operational_memory_preserves_failure_memory_honestly():
    memory = OperationalMemory()

    result = memory.capture(
        _capture_request(
            memory_type="failure",
            event_type="provider_failure",
            errors=("provider timeout",),
            warnings=("retry needed",),
            risk_level="elevated",
        )
    )

    assert result.status == "captured"
    assert result.critical_memory_preserved is True
    assert result.errors == ("provider timeout",)
    assert result.warnings == ("retry needed",)


def test_operational_memory_contains_internal_errors(monkeypatch):
    memory = OperationalMemory()

    def broken_record(*args, **kwargs):
        raise RuntimeError("memory storage exploded")

    monkeypatch.setattr(memory, "_memory_record", broken_record)

    result = memory.capture(_capture_request())

    assert result.status == "error"
    assert result.success is False
    assert "operational_memory_error_contained" in result.reasons
