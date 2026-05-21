from app.runner.audit_request_system import AuditRequestInput, AuditRequestSystem
from app.runner.self_validation import SelfValidation, SelfValidationRequest
from app.services.runtime_status import RuntimeStatus


def _valid_self_validation():
    return SelfValidation().validate(
        SelfValidationRequest(
            execution_id="execution-1",
            task_id="task-1",
            outputs=("Implemented audit request.",),
            modified_files=("app/runner/audit_request_system.py",),
            runtime_state={"status": "online", "loop_state": "active"},
        )
    )


def test_audit_request_creates_pending_request_from_self_validation():
    status = RuntimeStatus()
    system = AuditRequestSystem(status=status)
    validation = _valid_self_validation()

    result = system.request(
        AuditRequestInput(
            validation_result=validation,
            execution_summary="Audit request implementation complete.",
            runtime_state={"status": "online", "loop_state": "active"},
            metadata={"phase": "5.3.2"},
        )
    )

    assert result.status == "pending"
    assert result.success is True
    assert result.audit_status == "pending"
    assert result.audit_type == "file"
    assert result.execution_id == "execution-1"
    assert result.validation_status == "valid"
    assert result.continuation_frozen is True
    assert result.continuation_status == "frozen_waiting_audit"
    assert result.traceability_preserved is True
    assert result.delivery_targets == ("sentinel",)
    assert result.delivery_status == "prepared"
    assert result.audit_package_hash
    assert [entry["state"] for entry in result.audit_lifecycle] == [
        "requested",
        "pending",
    ]

    metrics = status.audit_request_metrics()
    assert metrics["audit_request_status"] == "pending"
    assert metrics["audit_requests_pending"] == 1
    assert metrics["continuation_frozen"] is True


def test_audit_request_accepts_invalid_validation_for_external_review():
    validation = SelfValidation().validate(
        SelfValidationRequest(
            execution_id="execution-1",
            task_id="task-1",
            outputs=("Runtime core changed.",),
            modified_files=("app/runner/runtime_loop.py",),
        )
    )
    system = AuditRequestSystem()

    result = system.request(AuditRequestInput(validation_result=validation))

    assert result.status == "pending"
    assert result.validation_status == "invalid"
    assert result.risk_status == "critical"
    assert result.audit_type == "architecture"
    assert result.continuation_frozen is True


def test_audit_request_blocks_incomplete_package():
    system = AuditRequestSystem()

    result = system.request(AuditRequestInput(execution_id="execution-1"))

    assert result.status == "blocked"
    assert result.success is False
    assert result.continuation_frozen is True
    assert result.delivery_status == "blocked"
    assert "missing_validation_status" in result.reasons
    assert "missing_risk_status" in result.reasons
    assert "missing_audit_package" in result.reasons


def test_audit_request_selects_security_audit_for_security_risk():
    validation = SelfValidation().validate(
        SelfValidationRequest(
            execution_id="execution-1",
            outputs=("Secret handling changed.",),
            modified_files=("app/runner/provider_bridge.py",),
            risk_notes=("security secret exposure",),
        )
    )
    system = AuditRequestSystem()

    result = system.request(AuditRequestInput(validation_result=validation))

    assert result.status == "pending"
    assert result.audit_type == "security"
    assert "severe_risk_detected" in result.audit_package["inconsistencies"]


def test_audit_request_contains_internal_errors(monkeypatch):
    system = AuditRequestSystem()

    def broken_package(*args, **kwargs):
        raise RuntimeError("audit package exploded")

    monkeypatch.setattr(system, "_audit_package", broken_package)

    result = system.request(AuditRequestInput(execution_id="execution-1"))

    assert result.status == "error"
    assert result.success is False
    assert result.continuation_frozen is True
    assert result.audit_status == "error"
    assert "audit_request_error_contained" in result.reasons
