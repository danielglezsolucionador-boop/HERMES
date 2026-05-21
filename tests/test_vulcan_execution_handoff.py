from app.runner.vulcan_execution_handoff import (
    VulcanExecutionHandoff,
    VulcanHandoffRequest,
)
from app.runner.vulcan_prompt_protocol import (
    VulcanPromptProtocol,
    VulcanPromptRequest,
)
from app.runner.vulcan_scope_enforcement import (
    VulcanScopeEnforcement,
    VulcanScopeRequest,
)
from app.services.runtime_status import RuntimeStatus


def _successful_scope():
    protocol = VulcanPromptProtocol().interpret(
        VulcanPromptRequest(
            execution_objective="create vulcan handoff",
            technical_scope="backend",
            file_targets=(
                "app/runner/vulcan_execution_handoff.py",
                "tests/test_vulcan_execution_handoff.py",
            ),
            allowed_file_targets=("app/runner/", "tests/"),
        )
    )
    scope = VulcanScopeEnforcement().enforce(
        VulcanScopeRequest(
            execution_id="execution-1",
            authorized_files=("app/runner/", "tests/"),
            proposed_files=("app/runner/vulcan_execution_handoff.py",),
            modified_files=("tests/test_vulcan_execution_handoff.py",),
            prompt_protocol=protocol,
            runtime_status="active",
            governance_status="approved",
        )
    )
    return protocol, scope


def test_vulcan_execution_handoff_generates_structured_handoff_and_metrics():
    protocol, scope = _successful_scope()
    status = RuntimeStatus()
    handoff = VulcanExecutionHandoff(status=status)

    result = handoff.generate(
        VulcanHandoffRequest(
            subphase_id="6.3_VULCAN_EXECUTION_HANDOFF.md",
            execution_objective="generate controlled execution handoff",
            modified_files=(
                "app/runner/vulcan_execution_handoff.py",
                "tests/test_vulcan_execution_handoff.py",
            ),
            implementation_summary=(
                "added isolated handoff generator",
                "published runtime metrics",
            ),
            validations_executed=("python -m py_compile", "pytest"),
            tests_executed=("pytest -q tests/test_vulcan_execution_handoff.py",),
            risks_detected=("runtime core untouched",),
            blocking_conditions=("failed validation blocks continuation",),
            not_implemented=("workflow execution",),
            operational_status="stable",
            governance_status="approved",
            execution_continuity="ready_for_next_subphase",
            prompt_protocol=protocol,
            scope_enforcement=scope,
        )
    )

    assert result.status == "generated"
    assert result.success is True
    assert result.handoff_complete is True
    assert result.traceability_preserved is True
    assert result.runtime_reporting_preserved is True
    assert result.validations_honest is True
    assert "SUBFASE: 6.3_VULCAN_EXECUTION_HANDOFF.md" in result.handoff_text
    assert "ARCHIVOS TOCADOS:" in result.handoff_text
    assert "CONTINUIDAD: ready_for_next_subphase" in result.handoff_text

    metrics = status.vulcan_execution_handoff_metrics()
    assert metrics["vulcan_execution_handoff_status"] == "generated"
    assert metrics["vulcan_execution_handoff_generated"] == 1
    assert metrics["handoff_complete"] is True


def test_vulcan_execution_handoff_blocks_incomplete_or_false_reporting():
    handoff = VulcanExecutionHandoff()

    result = handoff.generate(
        VulcanHandoffRequest(
            subphase_id="6.3_VULCAN_EXECUTION_HANDOFF.md",
            execution_objective="generate handoff",
            modified_files=("app/runner/vulcan_execution_handoff.py",),
            implementation_summary=("added handoff",),
            risks_detected=("validation missing",),
            blocking_conditions=("missing validation blocks continuation",),
            operational_status="stable",
            governance_status="approved",
            execution_continuity="blocked_until_validation",
            falsify_validations_requested=True,
            conceal_errors_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "validations_executed_required" in result.reasons
    assert "tests_executed_required" in result.reasons
    assert "validation_falsification_blocked" in result.reasons
    assert "error_concealment_blocked" in result.reasons
    assert result.handoff_complete is False
    assert result.validations_honest is False


def test_vulcan_execution_handoff_blocks_failed_scope_enforcement():
    handoff = VulcanExecutionHandoff()

    result = handoff.report(
        VulcanHandoffRequest(
            subphase_id="6.3_VULCAN_EXECUTION_HANDOFF.md",
            execution_objective="generate handoff",
            modified_files=("app/runner/vulcan_execution_handoff.py",),
            implementation_summary=("added handoff",),
            validations_executed=("python -m py_compile",),
            tests_executed=("pytest",),
            risks_detected=("scope blocked",),
            blocking_conditions=("scope enforcement must pass",),
            operational_status="stable",
            governance_status="approved",
            execution_continuity="blocked",
            scope_enforcement={"status": "blocked"},
        )
    )

    assert result.status == "blocked"
    assert "vulcan_scope_enforcement_not_enforced" in result.reasons
    assert result.execution_continuity == "blocked"


def test_vulcan_execution_handoff_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    handoff = VulcanExecutionHandoff(status=status)

    def broken_validation(*args, **kwargs):
        raise RuntimeError("handoff validation exploded")

    monkeypatch.setattr(handoff, "_validation_reasons", broken_validation)

    result = handoff.generate(
        VulcanHandoffRequest(
            subphase_id="6.3_VULCAN_EXECUTION_HANDOFF.md",
            execution_objective="generate handoff",
            modified_files=("app/runner/vulcan_execution_handoff.py",),
            implementation_summary=("added handoff",),
            validations_executed=("python -m py_compile",),
            tests_executed=("pytest",),
            risks_detected=("runtime core untouched",),
            blocking_conditions=("failed validation blocks continuation",),
            operational_status="stable",
            governance_status="approved",
            execution_continuity="ready",
        )
    )

    assert result.status == "error"
    assert "vulcan_execution_handoff_error_contained" in result.reasons

    metrics = status.vulcan_execution_handoff_metrics()
    assert metrics["vulcan_execution_handoff_status"] == "error"
    assert metrics["vulcan_execution_handoff_errors"] == 1
