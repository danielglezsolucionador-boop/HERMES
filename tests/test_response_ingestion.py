from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from app.models.task import Task
from app.runner.provider_bridge import (
    ProviderBridgeContext,
    ProviderBridgeResult,
)
from app.runner.response_ingestion import (
    ResponseIngestionRequest,
    ResponseIngestionRuntime,
)
from app.runner.task_execution import TaskExecutionRuntime


def _execution_context():
    task = Task(
        id=uuid4(),
        title="response ingestion task",
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
    provider_context = ProviderBridgeContext(
        request_id="provider-request-1",
        execution_id=execution.execution_id,
        task_id=execution.task_id,
        runner_id=execution.runner_id,
        runtime_id=execution.runtime_id,
        runtime_owner=execution.runtime_owner,
        provider_name="fake",
        built_at=datetime.now(timezone.utc).isoformat(),
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
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=5,
        provider_duration_ms=4,
        usage={"input_tokens": 2, "output_tokens": 3},
        max_response_bytes=32768,
        response_size_bytes=len(content.encode("utf-8")),
        context=provider_context,
    )


def test_response_ingestion_receives_response_and_preserves_context():
    execution = _execution_context()
    response = _provider_response(execution)
    runtime = ResponseIngestionRuntime()

    result = runtime.ingest(
        ResponseIngestionRequest(
            response=response,
            execution=execution,
            metadata={"source": "unit-test"},
        )
    )

    assert result.status == "ingested"
    assert result.success is True
    assert result.ingestion_state == "received"
    assert result.response_id
    assert result.execution_id == execution.execution_id
    assert result.task_id == execution.task_id
    assert result.runtime_id == execution.runtime_id
    assert result.execution_owner == execution.runtime_owner
    assert result.provider_source == "fake"
    assert result.provider_request_id == "provider-request-1"
    assert result.validation_status == "validated"
    assert result.validation_state == "accepted"
    assert result.storage_prepared is True
    assert result.metadata["source"] == "unit-test"
    assert runtime.visibility()["active_ingestions"] == 0


def test_response_ingestion_rejects_missing_or_inactive_inputs():
    runtime = ResponseIngestionRuntime()
    execution = replace(_execution_context(), execution_state="completed")

    result = runtime.ingest(
        ResponseIngestionRequest(response=None, execution=execution),
        runtime_active=False,
    )

    assert result.status == "rejected"
    assert "runtime_inactive" in result.reasons
    assert "missing_provider_response" in result.reasons
    assert "execution_not_active" in result.reasons


def test_response_ingestion_rejects_orphan_response_without_execution_linkage():
    runtime = ResponseIngestionRuntime()
    response = {
        "status": "completed",
        "success": True,
        "provider_name": "fake",
        "content": "provider answer",
    }

    result = runtime.ingest(ResponseIngestionRequest(response=response))

    assert result.status == "rejected"
    assert "missing_execution_id" in result.reasons
    assert "missing_task_id" in result.reasons
    assert "missing_runtime_id" in result.reasons
    assert "missing_execution_owner" in result.reasons


def test_response_ingestion_rejects_provider_failure_response():
    execution = _execution_context()
    response = ProviderBridgeResult(
        status="provider_error",
        success=False,
        provider_name="fake",
        request_id="provider-request-1",
        execution_id=execution.execution_id,
        task_id=execution.task_id,
        error="provider unavailable",
        reasons=("provider_error",),
    )
    runtime = ResponseIngestionRuntime()

    result = runtime.ingest(
        ResponseIngestionRequest(response=response, execution=execution)
    )

    assert result.status == "rejected"
    assert "provider_response_not_completed" in result.reasons
    assert "empty_response_content" in result.reasons


def test_response_ingestion_rejects_validation_failures_before_storage_preparation():
    execution = _execution_context()
    response = _provider_response(execution)
    response = replace(response, finished_at="not-a-timestamp")
    runtime = ResponseIngestionRuntime()

    result = runtime.ingest(
        ResponseIngestionRequest(response=response, execution=execution)
    )

    assert result.status == "rejected"
    assert result.ingestion_state == "validation_rejected"
    assert result.validation_status == "rejected"
    assert "invalid_finished_at" in result.reasons
    assert result.storage_prepared is False


def test_response_ingestion_enforces_response_size_and_concurrency():
    execution = _execution_context()
    size_limited = ResponseIngestionRuntime(max_response_bytes=4)

    too_large = size_limited.ingest(
        ResponseIngestionRequest(
            response=_provider_response(execution, content="too large"),
            execution=execution,
        )
    )

    assert too_large.status == "rejected"
    assert "max_response_size_exceeded" in too_large.reasons

    concurrent_limited = ResponseIngestionRuntime(max_concurrent_ingestions=1)
    concurrent_limited._active_ingestions = 1

    blocked = concurrent_limited.ingest(
        ResponseIngestionRequest(
            response=_provider_response(execution),
            execution=execution,
        )
    )

    assert blocked.status == "rejected"
    assert "max_concurrent_ingestions_reached" in blocked.reasons


def test_response_ingestion_enforces_runtime_ingestion_load():
    execution = _execution_context()
    runtime = ResponseIngestionRuntime(
        max_concurrent_ingestions=2,
        max_runtime_ingestion_load=0.4,
    )
    runtime._active_ingestions = 1

    result = runtime.ingest(
        ResponseIngestionRequest(
            response=_provider_response(execution),
            execution=execution,
        )
    )

    assert result.status == "rejected"
    assert "max_runtime_ingestion_load_reached" in result.reasons


def test_response_ingestion_result_does_not_expose_content_in_dict():
    execution = _execution_context()
    runtime = ResponseIngestionRuntime()

    result = runtime.ingest(
        ResponseIngestionRequest(
            response=_provider_response(execution, content="secret content"),
            execution=execution,
        )
    )

    payload = result.to_dict()

    assert result.status == "ingested"
    assert "content" not in payload
    assert payload["response_size_bytes"] == len("secret content".encode("utf-8"))
