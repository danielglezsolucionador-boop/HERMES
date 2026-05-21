from app.runner.executive_communication_flow import (
    ExecutiveCommunicationFlow,
    ExecutiveCommunicationRequest,
)
from app.services.runtime_status import RuntimeStatus


def test_executive_communication_accepts_ceo_execution_request_and_metrics():
    status = RuntimeStatus()
    flow = ExecutiveCommunicationFlow(status=status)

    result = flow.handle(
        ExecutiveCommunicationRequest(
            authority_source="CEO",
            communication_type="execution",
            instruction_type="execution_request",
            execution_context={"task_id": "task-1"},
            governance_status="approved",
            operational_status="ready",
        )
    )

    assert result.status == "accepted"
    assert result.success is True
    assert result.authority_identified is True
    assert result.response_target == "CEO"
    assert result.response_target_valid is True
    assert result.execution_transparency_preserved is True

    metrics = status.executive_communication_metrics()
    assert metrics["executive_communication_status"] == "accepted"
    assert metrics["executive_communications_accepted"] == 1
    assert metrics["authority_source"] == "CEO"


def test_executive_communication_reports_to_cerebro_source():
    flow = ExecutiveCommunicationFlow()

    result = flow.handle(
        ExecutiveCommunicationRequest(
            authority_source="CEREBRO",
            communication_type="governance",
            instruction_type="status_request",
            report_status="completed",
            governance_status="approved",
            operational_status="active",
            risks=("none",),
        )
    )

    assert result.status == "reported"
    assert result.response_target == "CEREBRO"
    assert result.report_payload["report_status"] == "completed"
    assert result.operational_continuity_preserved is True


def test_executive_communication_allows_sentinel_audit_context_request():
    flow = ExecutiveCommunicationFlow()

    result = flow.route(
        ExecutiveCommunicationRequest(
            authority_source="SENTINEL",
            communication_type="audit",
            instruction_type="audit_context_request",
            audit_status="requested",
            execution_context={"execution_id": "execution-1"},
        )
    )

    assert result.status == "accepted"
    assert result.response_target == "SENTINEL"
    assert result.audit_consistency_preserved is True


def test_executive_communication_blocks_unknown_authority():
    flow = ExecutiveCommunicationFlow()

    result = flow.handle(
        ExecutiveCommunicationRequest(
            authority_source="UNKNOWN",
            communication_type="execution",
        )
    )

    assert result.status == "blocked"
    assert "unknown_authority_source" in result.reasons
    assert result.authority_identified is False


def test_executive_communication_blocks_response_redirection():
    flow = ExecutiveCommunicationFlow()

    result = flow.handle(
        ExecutiveCommunicationRequest(
            authority_source="CEO",
            communication_type="execution",
            requested_response_target="CEREBRO",
        )
    )

    assert result.status == "blocked"
    assert "response_redirection_blocked" in result.reasons
    assert result.response_target_valid is False


def test_executive_communication_blocks_executive_orchestration():
    flow = ExecutiveCommunicationFlow()

    result = flow.handle(
        ExecutiveCommunicationRequest(
            authority_source="CEREBRO",
            communication_type="execution",
            executive_orchestration_requested=True,
            distribute_work_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "executive_orchestration_blocked" in result.reasons
    assert result.executive_orchestration_blocked is True


def test_executive_communication_blocks_dishonest_reporting():
    flow = ExecutiveCommunicationFlow()

    result = flow.handle(
        ExecutiveCommunicationRequest(
            authority_source="CEO",
            communication_type="governance",
            conceal_errors_requested=True,
            minimize_risks_requested=True,
            falsify_status_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "dishonest_reporting_blocked" in result.reasons
    assert result.honest_reporting_preserved is False
    assert result.execution_transparency_preserved is False


def test_executive_communication_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    flow = ExecutiveCommunicationFlow(status=status)

    def broken_registry(*args, **kwargs):
        raise RuntimeError("communication registry exploded")

    monkeypatch.setattr(flow.registry, "get_system", broken_registry)

    result = flow.handle(
        ExecutiveCommunicationRequest(authority_source="CEO")
    )

    assert result.status == "error"
    assert result.success is False
    assert "executive_communication_error_contained" in result.reasons
    metrics = status.executive_communication_metrics()
    assert metrics["executive_communication_errors"] == 1
