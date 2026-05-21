from app.runner.vulcan_execution_handoff import (
    VulcanExecutionHandoff,
    VulcanHandoffRequest,
)
from app.runner.vulcan_operational_validation import (
    VulcanOperationalValidation,
    VulcanOperationalValidationRequest,
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


def _successful_vulcan_chain():
    protocol = VulcanPromptProtocol().interpret(
        VulcanPromptRequest(
            execution_objective="validate vulcan workflow",
            technical_scope="backend",
            file_targets=(
                "app/runner/vulcan_operational_validation.py",
                "tests/test_vulcan_operational_validation.py",
            ),
            allowed_file_targets=("app/runner/", "tests/"),
        )
    )
    scope = VulcanScopeEnforcement().enforce(
        VulcanScopeRequest(
            execution_id="execution-1",
            authorized_files=("app/runner/", "tests/"),
            proposed_files=("app/runner/vulcan_operational_validation.py",),
            modified_files=("tests/test_vulcan_operational_validation.py",),
            prompt_protocol=protocol,
            runtime_status="active",
            governance_status="approved",
        )
    )
    handoff = VulcanExecutionHandoff().generate(
        VulcanHandoffRequest(
            subphase_id="6.4_VULCAN_OPERATIONAL_VALIDATION.md",
            execution_objective="validate vulcan workflow",
            modified_files=(
                "app/runner/vulcan_operational_validation.py",
                "tests/test_vulcan_operational_validation.py",
            ),
            implementation_summary=("added operational validation",),
            validations_executed=("python -m py_compile", "pytest"),
            tests_executed=("pytest -q tests/test_vulcan_operational_validation.py",),
            risks_detected=("runtime core untouched",),
            blocking_conditions=("none",),
            not_implemented=("command execution",),
            operational_status="stable",
            governance_status="approved",
            execution_continuity="ready_for_next_subphase",
            prompt_protocol=protocol,
            scope_enforcement=scope,
        )
    )
    return protocol, scope, handoff


def test_vulcan_operational_validation_authorizes_stable_workflow_and_metrics():
    protocol, scope, handoff = _successful_vulcan_chain()
    status = RuntimeStatus()
    validator = VulcanOperationalValidation(status=status)

    result = validator.validate(
        VulcanOperationalValidationRequest(
            subphase_id="6.4_VULCAN_OPERATIONAL_VALIDATION.md",
            modified_files=(
                "app/runner/vulcan_operational_validation.py",
                "tests/test_vulcan_operational_validation.py",
            ),
            runtime_validation="passed",
            import_validation="passed",
            architecture_validation="stable",
            execution_validation="valid",
            governance_validation="approved",
            security_validation="safe",
            validations_executed=("python -m py_compile", "python -c import main"),
            tests_executed=("pytest -q",),
            blocking_conditions=("none",),
            prompt_protocol=protocol,
            scope_enforcement=scope,
            execution_handoff=handoff,
            runtime_status="active",
            governance_status="approved",
            security_status="clear",
            architecture_status="stable",
        )
    )

    assert result.status == "validated"
    assert result.success is True
    assert result.runtime_valid is True
    assert result.imports_valid is True
    assert result.architecture_valid is True
    assert result.execution_consistent is True
    assert result.governance_compliant is True
    assert result.security_safe is True
    assert result.continuation_authorized is True
    assert result.continuation_status == "authorized"

    metrics = status.vulcan_operational_validation_metrics()
    assert metrics["vulcan_operational_validation_status"] == "validated"
    assert metrics["vulcan_operational_validation_validated"] == 1
    assert metrics["vulcan_operational_validation_errors"] == 0
    assert metrics["operational_continuity_preserved"] is True


def test_vulcan_operational_validation_blocks_runtime_import_and_blockers():
    validator = VulcanOperationalValidation()

    result = validator.validate(
        VulcanOperationalValidationRequest(
            subphase_id="6.4_VULCAN_OPERATIONAL_VALIDATION.md",
            modified_files=("app/runner/vulcan_operational_validation.py",),
            runtime_validation="failed",
            import_validation="failed",
            architecture_validation="stable",
            execution_validation="valid",
            governance_validation="approved",
            security_validation="safe",
            validations_executed=("python -m py_compile",),
            tests_executed=("pytest",),
            blocking_conditions=("runtime corruption",),
            runtime_status="critical",
            governance_status="approved",
            security_status="clear",
            architecture_status="stable",
        )
    )

    assert result.status == "blocked"
    assert "runtime_validation_failed" in result.reasons
    assert "imports_validation_failed" in result.reasons
    assert "blocking_conditions_active" in result.reasons
    assert "runtime_status_unsafe" in result.reasons
    assert result.continuation_authorized is False
    assert result.operational_continuity_preserved is False


def test_vulcan_operational_validation_blocks_false_validation_requests():
    validator = VulcanOperationalValidation()

    result = validator.assess(
        VulcanOperationalValidationRequest(
            subphase_id="6.4_VULCAN_OPERATIONAL_VALIDATION.md",
            modified_files=("app/runner/vulcan_operational_validation.py",),
            runtime_validation=True,
            import_validation=True,
            architecture_validation=True,
            execution_validation=True,
            governance_validation=True,
            security_validation=True,
            validations_executed=("python -m py_compile",),
            tests_executed=("pytest",),
            blocking_conditions=("none",),
            falsify_validations_requested=True,
            ignore_runtime_failures_requested=True,
            hide_inconsistencies_requested=True,
            approve_corrupt_workflow_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "false_validation_blocked" in result.reasons
    assert "runtime_failure_ignored_blocked" in result.reasons
    assert "inconsistency_concealment_blocked" in result.reasons
    assert "corrupt_workflow_approval_blocked" in result.reasons
    assert result.technical_reporting_honest is False


def test_vulcan_operational_validation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    validator = VulcanOperationalValidation(status=status)

    def broken_validation(*args, **kwargs):
        raise RuntimeError("operational validation exploded")

    monkeypatch.setattr(validator, "_validation_reasons", broken_validation)

    result = validator.validate(
        VulcanOperationalValidationRequest(
            subphase_id="6.4_VULCAN_OPERATIONAL_VALIDATION.md",
            modified_files=("app/runner/vulcan_operational_validation.py",),
            runtime_validation=True,
            import_validation=True,
            architecture_validation=True,
            execution_validation=True,
            governance_validation=True,
            security_validation=True,
            validations_executed=("python -m py_compile",),
            tests_executed=("pytest",),
            blocking_conditions=("none",),
        )
    )

    assert result.status == "error"
    assert "vulcan_operational_validation_error_contained" in result.reasons

    metrics = status.vulcan_operational_validation_metrics()
    assert metrics["vulcan_operational_validation_status"] == "error"
    assert metrics["vulcan_operational_validation_errors"] == 1
