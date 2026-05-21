from app.runner.provider_bridge import ProviderBridgeResult
from app.runner.provider_failure_control import (
    ProviderFailureControl,
    ProviderFailureControlRequest,
)
from app.runner.provider_response_handling import ProviderResponseHandlingResult
from app.services.runtime_status import RuntimeStatus


def _provider_result(
    status: str = "timeout",
    success: bool = False,
    reasons: tuple[str, ...] = ("provider_timeout",),
    error: str | None = "provider timed out",
) -> ProviderBridgeResult:
    return ProviderBridgeResult(
        status=status,
        success=success,
        provider_name="fake",
        provider_session_id="provider-session-1",
        request_id="provider-request-1",
        execution_id="execution-1",
        task_id="task-1",
        reasons=reasons,
        error=error,
        failure_status=",".join(reasons) if reasons else None,
    )


def test_provider_failure_control_blocks_connection_failure_and_preserves_context():
    status = RuntimeStatus()
    control = ProviderFailureControl(status=status)

    result = control.record(
        ProviderFailureControlRequest(
            signal=_provider_result(),
            runtime_state="active",
            metadata={"phase": "5.2.4"},
        )
    )

    assert result.status == "blocked"
    assert result.failure_detected is True
    assert result.failure_type == "connection"
    assert result.failure_severity == "high"
    assert result.failure_status == "recovery_pending"
    assert result.recovery_status == "recovery_pending"
    assert result.continuation_blocked is True
    assert result.context_preserved is True
    assert result.recovery_prepared is True
    assert result.provider_id == "fake"
    assert result.execution_id == "execution-1"
    assert [entry["state"] for entry in result.lifecycle] == [
        "detected",
        "registered",
        "contained",
        "blocked",
        "recovery_pending",
    ]

    metrics = status.provider_failure_control_metrics()
    assert metrics["provider_failure_control_status"] == "blocked"
    assert metrics["provider_failures_detected"] == 1
    assert metrics["provider_failures_blocked"] == 1
    assert metrics["recovery_status"] == "recovery_pending"


def test_provider_failure_control_escalates_critical_credentials_failure():
    control = ProviderFailureControl()
    signal = _provider_result(
        status="rejected",
        reasons=("provider_not_configured", "invalid_credentials"),
        error="missing api key",
    )

    result = control.record(ProviderFailureControlRequest(signal=signal))

    assert result.status == "escalated"
    assert result.failure_type == "connection"
    assert result.failure_severity == "critical"
    assert result.escalation_required is True
    assert "provider_not_configured" in result.reasons
    assert "escalated" in [entry["state"] for entry in result.lifecycle]


def test_provider_failure_control_classifies_response_failure():
    control = ProviderFailureControl()
    handling_result = ProviderResponseHandlingResult(
        status="rejected",
        success=False,
        handling_id="handling-1",
        response_status="rejected",
        response_type="failure",
        provider_id="fake",
        provider_request_id="provider-request-1",
        execution_id="execution-1",
        task_id="task-1",
        reasons=("empty_response_content", "malformed_provider_output"),
        error="empty provider response",
    )

    result = control.record(ProviderFailureControlRequest(signal=handling_result))

    assert result.status == "blocked"
    assert result.failure_type == "response"
    assert result.failure_severity == "medium"
    assert result.provider_request_id == "provider-request-1"
    assert result.execution_impact == "blocked"


def test_provider_failure_control_returns_clear_for_successful_provider_result():
    status = RuntimeStatus()
    control = ProviderFailureControl(status=status)
    signal = _provider_result(
        status="completed",
        success=True,
        reasons=(),
        error=None,
    )

    result = control.record(ProviderFailureControlRequest(signal=signal))

    assert result.status == "clear"
    assert result.success is True
    assert result.failure_detected is False
    assert result.continuation_blocked is False
    assert result.recovery_status == "not_required"
    assert result.lifecycle == ()
    assert status.provider_failure_control_metrics()["provider_failures_detected"] == 0


def test_provider_failure_control_contains_internal_errors(monkeypatch):
    control = ProviderFailureControl()

    def broken_signal(value):
        raise RuntimeError("failure context exploded")

    monkeypatch.setattr(control, "_as_dict", broken_signal)

    result = control.record(ProviderFailureControlRequest(signal={}))

    assert result.status == "error"
    assert result.failure_detected is True
    assert result.runtime_protected is True
    assert result.failure_type == "runtime"
    assert result.failure_severity == "critical"
    assert result.escalation_required is True
    assert "provider_failure_control_error_contained" in result.reasons
