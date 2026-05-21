from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models.task import Task
from app.runner.provider_bridge import (
    ProviderBridgeContext,
    ProviderBridgeResult,
)
from app.runner.response_validation import (
    ResponseValidationRequest,
    ResponseValidationRuntime,
)
from app.runner.task_execution import TaskExecutionRuntime


def _execution_context():
    task = Task(
        id=uuid4(),
        title="response validation task",
        status="claimed",
        phase="test",
        runner_id="runner-test",
        runtime_id="runtime-test",
        claim_state="claimed",
        claimed_at=datetime.now(timezone.utc),
        claim_attempts=1,
    )
    runtime = TaskExecutionRuntime(
        runner_id="runner-test",
        runtime_id="runtime-test",
        memory_usage_provider=lambda: 64,
    )
    prepared = runtime.prepare(task)
    started = runtime.start(prepared.context)
    return started.context


def _provider_response(execution=None, content: str = "provider answer"):
    execution = execution or _execution_context()
    started_at = datetime.now(timezone.utc)
    finished_at = started_at + timedelta(milliseconds=5)
    provider_context = ProviderBridgeContext(
        request_id="provider-request-1",
        execution_id=execution.execution_id,
        task_id=execution.task_id,
        runner_id=execution.runner_id,
        runtime_id=execution.runtime_id,
        runtime_owner=execution.runtime_owner,
        provider_name="fake",
        built_at=started_at.isoformat(),
        request_size_bytes=12,
        timeout_seconds=25.0,
        max_tokens=128,
    )
    return ProviderBridgeResult(
        status="completed",
        success=True,
        provider_name="fake",
        model="fake-model",
        content=content,
        request_id="provider-request-1",
        execution_id=execution.execution_id,
        task_id=execution.task_id,
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        duration_ms=5,
        provider_duration_ms=4,
        usage={"input_tokens": 2, "output_tokens": 3},
        max_response_bytes=32768,
        response_size_bytes=len(content.encode("utf-8")),
        context=provider_context,
    )


def test_response_validation_accepts_valid_response_and_preserves_context(caplog):
    execution = _execution_context()
    response = _provider_response(execution)
    runtime = ResponseValidationRuntime()
    caplog.set_level("INFO")

    result = runtime.validate(
        ResponseValidationRequest(
            response=response,
            execution=execution,
            metadata={"source": "unit-test"},
        )
    )

    assert result.status == "validated"
    assert result.success is True
    assert result.validation_state == "accepted"
    assert result.validation_id
    assert result.execution_id == execution.execution_id
    assert result.task_id == execution.task_id
    assert result.runtime_id == execution.runtime_id
    assert result.execution_owner == execution.runtime_owner
    assert result.provider_source == "fake"
    assert result.provider_request_id == "provider-request-1"
    assert result.metadata["source"] == "unit-test"
    assert runtime.visibility()["active_validations"] == 0
    assert "response_validation: validated" in caplog.text


def test_response_validation_rejects_missing_or_inactive_inputs(caplog):
    runtime = ResponseValidationRuntime()
    execution = replace(_execution_context(), execution_state="completed")
    caplog.set_level("WARNING")

    result = runtime.validate(
        ResponseValidationRequest(response=None, execution=execution),
        runtime_active=False,
    )

    assert result.status == "rejected"
    assert "runtime_inactive" in result.reasons
    assert "missing_provider_response" in result.reasons
    assert "execution_not_active" in result.reasons
    assert "response_validation: rejected" in caplog.text


def test_response_validation_rejects_corrupt_payload_structure():
    execution = _execution_context()
    now = datetime.now(timezone.utc).isoformat()
    response = {
        "status": "completed",
        "success": True,
        "provider_name": "fake",
        "content": "provider answer",
        "request_id": "provider-request-1",
        "execution_id": execution.execution_id,
        "task_id": execution.task_id,
        "runtime_id": execution.runtime_id,
        "runtime_owner": execution.runtime_owner,
        "started_at": now,
        "finished_at": now,
        "usage": "not-a-dict",
        "context": "not-a-dict",
        "reasons": "not-a-list",
    }
    runtime = ResponseValidationRuntime()

    result = runtime.validate(
        ResponseValidationRequest(
            response=response,
            execution=execution,
            metadata="not-a-dict",
        )
    )

    assert result.status == "rejected"
    assert "invalid_validation_metadata" in result.reasons
    assert "invalid_response_metadata" in result.reasons
    assert "invalid_response_context" in result.reasons
    assert "invalid_response_reasons" in result.reasons


def test_response_validation_rejects_execution_linkage_mismatch():
    execution = _execution_context()
    response = replace(_provider_response(execution), task_id=str(uuid4()))
    runtime = ResponseValidationRuntime()

    result = runtime.validate(
        ResponseValidationRequest(response=response, execution=execution)
    )

    assert result.status == "rejected"
    assert "task_id_mismatch" in result.reasons


def test_response_validation_rejects_timestamp_integrity_failure():
    execution = _execution_context()
    started_at = datetime.now(timezone.utc)
    response = replace(
        _provider_response(execution),
        started_at=started_at.isoformat(),
        finished_at=(started_at - timedelta(seconds=1)).isoformat(),
    )
    runtime = ResponseValidationRuntime()

    result = runtime.validate(
        ResponseValidationRequest(response=response, execution=execution)
    )

    assert result.status == "rejected"
    assert "response_timestamp_order_invalid" in result.reasons


def test_response_validation_enforces_payload_concurrency_load_and_duration_limits():
    execution = _execution_context()
    size_limited = ResponseValidationRuntime(max_payload_inspection_bytes=4)

    too_large = size_limited.validate(
        ResponseValidationRequest(
            response=_provider_response(execution, content="too large"),
            execution=execution,
        )
    )

    assert too_large.status == "rejected"
    assert "max_payload_inspection_exceeded" in too_large.reasons

    concurrent_limited = ResponseValidationRuntime(max_concurrent_validations=1)
    concurrent_limited._active_validations = 1
    blocked = concurrent_limited.validate(
        ResponseValidationRequest(
            response=_provider_response(execution),
            execution=execution,
        )
    )

    assert blocked.status == "rejected"
    assert "max_concurrent_validations_reached" in blocked.reasons

    load_limited = ResponseValidationRuntime(
        max_concurrent_validations=2,
        max_runtime_validation_load=0.4,
    )
    load_limited._active_validations = 1
    overloaded = load_limited.validate(
        ResponseValidationRequest(
            response=_provider_response(execution),
            execution=execution,
        )
    )

    assert overloaded.status == "rejected"
    assert "max_runtime_validation_load_reached" in overloaded.reasons

    duration_limited = ResponseValidationRuntime(max_validation_duration_ms=1)
    duration_limited._duration_ms = lambda started: 2
    timed_out = duration_limited.validate(
        ResponseValidationRequest(
            response=_provider_response(execution),
            execution=execution,
        )
    )

    assert timed_out.status == "rejected"
    assert "max_validation_duration_reached" in timed_out.reasons


def test_response_validation_contains_internal_errors():
    execution = _execution_context()
    runtime = ResponseValidationRuntime()

    def fail_build_context(*args, **kwargs):
        raise RuntimeError("validation context failure")

    runtime._build_context = fail_build_context
    result = runtime.validate(
        ResponseValidationRequest(
            response=_provider_response(execution),
            execution=execution,
        )
    )

    assert result.status == "error"
    assert "response_validation_error_contained" in result.reasons
    assert runtime.visibility()["active_validations"] == 0


def test_response_validation_result_does_not_expose_content_in_dict():
    execution = _execution_context()
    runtime = ResponseValidationRuntime()

    result = runtime.validate(
        ResponseValidationRequest(
            response=_provider_response(execution, content="secret content"),
            execution=execution,
        )
    )

    payload = result.to_dict()

    assert result.status == "validated"
    assert "content" not in payload
    assert payload["payload_size_bytes"] == len("secret content".encode("utf-8"))
