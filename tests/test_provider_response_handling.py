from datetime import datetime, timezone
from uuid import uuid4

from app.models.task import Task
from app.runner.prompt_execution import PromptExecutionResult
from app.runner.provider_bridge import ProviderBridgeContext, ProviderBridgeResult
from app.runner.provider_response_handling import (
    ProviderResponseHandler,
    ProviderResponseHandlingRequest,
)
from app.runner.task_execution import TaskExecutionRuntime
from app.services.runtime_status import RuntimeStatus


def _execution_context():
    task = Task(
        id=uuid4(),
        title="provider response handling task",
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


def _provider_response(execution=None, content: str = "provider output"):
    execution = execution or _execution_context()
    now = datetime.now(timezone.utc).isoformat()
    provider_context = ProviderBridgeContext(
        request_id="provider-request-1",
        execution_id=execution.execution_id,
        task_id=execution.task_id,
        runner_id=execution.runner_id,
        runtime_id=execution.runtime_id,
        runtime_owner=execution.runtime_owner,
        provider_name="fake",
        built_at=now,
        request_size_bytes=12,
        timeout_seconds=25.0,
        max_tokens=128,
        provider_session_id="provider-session-1",
    )
    return ProviderBridgeResult(
        status="completed",
        success=True,
        provider_name="fake",
        provider_session_id="provider-session-1",
        connection_status="closed",
        model="fake-model",
        content=content,
        request_id="provider-request-1",
        execution_id=execution.execution_id,
        task_id=execution.task_id,
        started_at=now,
        finished_at=now,
        duration_ms=5,
        provider_duration_ms=4,
        usage={"input_tokens": 2, "output_tokens": 3},
        max_response_bytes=32768,
        response_size_bytes=len(content.encode("utf-8")),
        context=provider_context,
    )


def test_provider_response_handling_validates_stores_and_prepares_audit():
    execution = _execution_context()
    status = RuntimeStatus()
    handler = ProviderResponseHandler(status=status)

    result = handler.handle(
        ProviderResponseHandlingRequest(
            response=_provider_response(execution),
            execution=execution,
            response_type="reporting",
            metadata={"phase": "5.2.3"},
        )
    )

    assert result.status == "handled"
    assert result.success is True
    assert result.response_status == "stored"
    assert result.response_type == "reporting"
    assert result.validation_status == "validated"
    assert result.audit_status == "audit_pending"
    assert result.output_available is True
    assert result.storage_prepared is True
    assert result.audit_package["response_id"] == result.response_id
    assert result.audit_package["provider_id"] == "fake"
    assert [entry["state"] for entry in result.lifecycle] == [
        "received",
        "validating",
        "validated",
        "audit_pending",
        "stored",
    ]

    metrics = status.provider_response_handling_metrics()
    assert metrics["provider_response_handling_status"] == "handled"
    assert metrics["response_status"] == "stored"
    assert metrics["provider_responses_handled"] == 1


def test_provider_response_handling_rejects_empty_output():
    execution = _execution_context()
    handler = ProviderResponseHandler()

    result = handler.handle(
        ProviderResponseHandlingRequest(
            response=_provider_response(execution, content=""),
            execution=execution,
        )
    )

    assert result.status == "rejected"
    assert result.success is False
    assert result.response_status == "rejected"
    assert result.audit_status == "blocked"
    assert "empty_response_content" in result.reasons
    assert result.storage_prepared is False


def test_provider_response_handling_blocks_provider_failure():
    execution = _execution_context()
    failed = ProviderBridgeResult(
        status="provider_error",
        success=False,
        provider_name="fake",
        request_id="provider-request-1",
        execution_id=execution.execution_id,
        task_id=execution.task_id,
        error="provider unavailable",
        reasons=("provider_error",),
    )
    handler = ProviderResponseHandler()

    result = handler.handle(
        ProviderResponseHandlingRequest(response=failed, execution=execution)
    )

    assert result.status == "rejected"
    assert result.response_status == "rejected"
    assert result.audit_status == "blocked"
    assert "provider_response_not_completed" in result.reasons


def test_provider_response_handling_classifies_prompt_execution_response():
    execution = _execution_context()
    provider_response = _provider_response(execution)
    prompt_result = PromptExecutionResult(
        status="completed",
        success=True,
        prompt_execution_id="prompt-execution-1",
        prompt_type="reporting",
        prompt_status="completed",
        objective="Report status",
        provider_name="fake",
        provider_session_id="provider-session-1",
        request_id="provider-request-1",
        execution_id=execution.execution_id,
        task_id=execution.task_id,
        output="provider output",
        output_size_bytes=len("provider output".encode("utf-8")),
        provider_result=provider_response,
    )
    handler = ProviderResponseHandler()

    result = handler.handle(
        ProviderResponseHandlingRequest(
            response=prompt_result,
            execution=execution,
            metadata={"phase": "5.2.3"},
        )
    )

    assert result.status == "handled"
    assert result.response_type == "reporting"
    assert result.audit_package["metadata"]["phase"] == "5.2.3"
    assert result.output_available is True
    assert "output" not in result.to_dict()
