from app.runner.vulcan_prompt_protocol import (
    VulcanPromptProtocol,
    VulcanPromptRequest,
)
from app.services.runtime_status import RuntimeStatus


def test_vulcan_prompt_protocol_interprets_backend_prompt_and_metrics():
    status = RuntimeStatus()
    protocol = VulcanPromptProtocol(status=status)

    result = protocol.interpret(
        VulcanPromptRequest(
            prompt="OBJETIVO: add controlled backend protocol observability",
            execution_objective="add controlled backend protocol observability",
            technical_scope="BackEnd",
            file_targets=(
                "app/runner/vulcan_prompt_protocol.py",
                "tests/test_vulcan_prompt_protocol.py",
            ),
            allowed_file_targets=("app/runner/", "tests/"),
            validation_requirements=("python -m py_compile app/runner/file.py",),
            risk_conditions=("runtime core must remain untouched",),
            blocking_conditions=("stop on failed required validation",),
            governance_status="approved",
            runtime_status="active",
        )
    )

    assert result.status == "interpreted"
    assert result.success is True
    assert result.technical_scope == "backend"
    assert result.prompt_interpreted is True
    assert result.file_targets_valid is True
    assert result.validations_identified is True
    assert result.architecture_integrity_preserved is True
    assert result.runtime_stability_preserved is True
    assert result.governance_consistency_preserved is True
    assert result.controlled_execution_ready is True
    assert "pytest" in result.validation_requirements
    assert 'python -c "import main"' in result.validation_requirements

    metrics = status.vulcan_prompt_protocol_metrics()
    assert metrics["vulcan_prompt_protocol_status"] == "interpreted"
    assert metrics["vulcan_prompt_protocol_interpreted"] == 1
    assert metrics["vulcan_prompt_protocol_errors"] == 0
    assert metrics["technical_scope"] == "backend"
    assert metrics["controlled_execution_ready"] is True


def test_vulcan_prompt_protocol_blocks_architecture_and_runtime_override():
    protocol = VulcanPromptProtocol()

    result = protocol.interpret(
        VulcanPromptRequest(
            execution_objective="change runtime governance",
            technical_scope="backend",
            file_targets=("app/runner/runtime_loop.py",),
            allowed_file_targets=("app/runner/",),
            architecture_override_requested=True,
            governance_runtime_modification_requested=True,
            runtime_core_modification_requested=True,
            scope_expansion_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert "architecture_override_blocked" in result.reasons
    assert "governance_runtime_modification_blocked" in result.reasons
    assert "runtime_core_modification_blocked" in result.reasons
    assert "scope_expansion_blocked" in result.reasons
    assert result.architecture_integrity_preserved is False
    assert result.runtime_stability_preserved is False
    assert result.governance_consistency_preserved is False
    assert result.execution_authorized is False


def test_vulcan_prompt_protocol_blocks_unauthorized_file_targets():
    protocol = VulcanPromptProtocol()

    result = protocol.assess(
        VulcanPromptRequest(
            execution_objective="add backend protocol test",
            technical_scope="tests",
            file_targets=("app/main.py",),
            allowed_file_targets=("tests/",),
            governance_status="approved",
            runtime_status="active",
        )
    )

    assert result.status == "blocked"
    assert "unauthorized_file_targets" in result.reasons
    assert result.file_targets_valid is False
    assert result.controlled_execution_ready is False


def test_vulcan_prompt_protocol_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    protocol = VulcanPromptProtocol(status=status)

    def broken_objective(*args, **kwargs):
        raise RuntimeError("prompt parser exploded")

    monkeypatch.setattr(protocol, "_objective", broken_objective)

    result = protocol.interpret(
        VulcanPromptRequest(
            execution_objective="validate error containment",
            technical_scope="backend",
            file_targets=("app/runner/vulcan_prompt_protocol.py",),
        )
    )

    assert result.status == "error"
    assert result.success is False
    assert "vulcan_prompt_protocol_error_contained" in result.reasons

    metrics = status.vulcan_prompt_protocol_metrics()
    assert metrics["vulcan_prompt_protocol_errors"] == 1
    assert metrics["vulcan_prompt_protocol_status"] == "error"
