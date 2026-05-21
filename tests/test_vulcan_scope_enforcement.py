from app.runner.vulcan_prompt_protocol import (
    VulcanPromptProtocol,
    VulcanPromptRequest,
)
from app.runner.vulcan_scope_enforcement import (
    VulcanScopeEnforcement,
    VulcanScopeRequest,
)
from app.services.runtime_status import RuntimeStatus


def test_vulcan_scope_enforcement_accepts_authorized_backend_scope():
    status = RuntimeStatus()
    protocol = VulcanPromptProtocol().interpret(
        VulcanPromptRequest(
            execution_objective="enforce backend scope",
            technical_scope="backend",
            file_targets=(
                "app/runner/vulcan_scope_enforcement.py",
                "tests/test_vulcan_scope_enforcement.py",
            ),
            allowed_file_targets=("app/runner/", "tests/"),
        )
    )
    enforcement = VulcanScopeEnforcement(status=status)

    result = enforcement.enforce(
        VulcanScopeRequest(
            execution_id="execution-1",
            authorized_files=("app/runner/", "tests/"),
            proposed_files=("app/runner/vulcan_scope_enforcement.py",),
            modified_files=("tests/test_vulcan_scope_enforcement.py",),
            execution_limits={"max_files": 3, "max_modified_files": 2},
            architecture_boundaries={
                "allow_runtime_core": False,
                "allow_governance_changes": False,
            },
            governance_restrictions=("no architecture override",),
            prompt_protocol=protocol,
            architecture_status="stable",
            runtime_status="active",
            governance_status="approved",
        )
    )

    assert result.status == "enforced"
    assert result.success is True
    assert result.scope_compliant is True
    assert result.files_authorized is True
    assert result.protected_systems_preserved is True
    assert result.execution_limits_preserved is True
    assert result.controlled_modification_ready is True
    assert result.execution_authorized is True

    metrics = status.vulcan_scope_enforcement_metrics()
    assert metrics["vulcan_scope_enforcement_status"] == "enforced"
    assert metrics["vulcan_scope_enforcement_enforced"] == 1
    assert metrics["vulcan_scope_enforcement_errors"] == 0
    assert metrics["files_authorized"] is True


def test_vulcan_scope_enforcement_blocks_unauthorized_file_targets():
    enforcement = VulcanScopeEnforcement()

    result = enforcement.enforce(
        VulcanScopeRequest(
            execution_id="execution-2",
            technical_scope="backend",
            authorized_files=("app/runner/",),
            proposed_files=("app/api/runtime.py",),
            modified_files=("app/main.py",),
            runtime_status="active",
            governance_status="approved",
        )
    )

    assert result.status == "blocked"
    assert "proposed_files_outside_authorized_scope" in result.reasons
    assert "modified_files_outside_authorized_scope" in result.reasons
    assert result.files_authorized is False
    assert result.execution_authorized is False


def test_vulcan_scope_enforcement_blocks_protected_runtime_boundary():
    enforcement = VulcanScopeEnforcement()

    result = enforcement.validate(
        VulcanScopeRequest(
            execution_id="execution-3",
            technical_scope="backend",
            authorized_files=("app/runner/",),
            proposed_files=("app/runner/runtime_loop.py",),
            architecture_boundaries={"allow_runtime_core": False},
            protected_systems=("runtime_core",),
            runtime_status="active",
            governance_status="approved",
        )
    )

    assert result.status == "blocked"
    assert "protected_system_boundary_violation" in result.reasons
    assert result.protected_systems_preserved is False
    assert result.operational_continuity_preserved is False


def test_vulcan_scope_enforcement_blocks_scope_expansion_and_dishonest_reporting():
    enforcement = VulcanScopeEnforcement()

    result = enforcement.enforce(
        VulcanScopeRequest(
            execution_id="execution-4",
            technical_scope="backend",
            authorized_files=("app/runner/",),
            proposed_files=("app/runner/vulcan_scope_enforcement.py",),
            scope_expansion_requested=True,
            full_system_refactor_requested=True,
            conceal_modified_files_requested=True,
            falsify_scope_requested=True,
            runtime_status="active",
            governance_status="approved",
        )
    )

    assert result.status == "blocked"
    assert "scope_expansion_blocked" in result.reasons
    assert "full_system_refactor_blocked" in result.reasons
    assert "dishonest_scope_reporting_blocked" in result.reasons
    assert result.execution_consistency_preserved is False
    assert result.reporting_honest is False


def test_vulcan_scope_enforcement_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    enforcement = VulcanScopeEnforcement(status=status)

    def broken_validation(*args, **kwargs):
        raise RuntimeError("scope parser exploded")

    monkeypatch.setattr(enforcement, "_validation_reasons", broken_validation)

    result = enforcement.enforce(
        VulcanScopeRequest(
            execution_id="execution-5",
            technical_scope="backend",
            authorized_files=("app/runner/",),
            proposed_files=("app/runner/vulcan_scope_enforcement.py",),
        )
    )

    assert result.status == "error"
    assert "vulcan_scope_enforcement_error_contained" in result.reasons

    metrics = status.vulcan_scope_enforcement_metrics()
    assert metrics["vulcan_scope_enforcement_status"] == "error"
    assert metrics["vulcan_scope_enforcement_errors"] == 1
