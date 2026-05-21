from app.runner.knowledge_core_validation import (
    KnowledgeCoreValidation,
    KnowledgeCoreValidationRequest,
)
from app.services.runtime_status import RuntimeStatus


def _valid_context():
    return {
        "knowledge_core": {
            "roadmap_consistency_valid": True,
            "governance_alignment_valid": True,
        },
        "phases_roadmap": {
            "roadmap_coherence_preserved": True,
            "phase_consistency_valid": True,
            "governance_alignment_valid": True,
            "execution_continuity_valid": True,
        },
        "apps_standards": {
            "standards_legitimacy_valid": True,
            "architecture_compatibility_valid": True,
            "governance_alignment_valid": True,
        },
        "dependency_context": {
            "dependency_integrity_valid": True,
            "runtime_compatibility_valid": True,
            "governance_alignment_valid": True,
            "operational_continuity_valid": True,
        },
    }


def test_knowledge_core_validation_approves_context_and_metrics():
    status = RuntimeStatus()
    validator = KnowledgeCoreValidation(status=status)

    result = validator.validate(KnowledgeCoreValidationRequest(**_valid_context()))

    assert result.status == "validated"
    assert result.success is True
    assert result.context_approved is True
    assert result.blocking_conditions == ()
    assert result.architecture_consistency_preserved is True
    assert result.operational_continuity_preserved is True

    metrics = status.knowledge_core_validation_metrics()
    assert metrics["knowledge_core_validation_status"] == "validated"
    assert metrics["knowledge_core_validation_validated"] == 1
    assert metrics["knowledge_core_validation_errors"] == 0
    assert metrics["context_approved"] is True


def test_knowledge_core_validation_blocks_invalid_context():
    validator = KnowledgeCoreValidation()
    context = _valid_context()
    context["dependency_context"]["runtime_compatibility_valid"] = False

    result = validator.validate(
        KnowledgeCoreValidationRequest(
            **context,
            detected_inconsistencies=("runtime dependency mismatch",),
        )
    )

    assert result.status == "blocked"
    assert result.context_approved is False
    assert "dependency_invalid" in result.reasons
    assert "knowledge_blocking_conditions_active" in result.reasons
    assert "dependency_validation_failed" in result.detected_inconsistencies
    assert "runtime dependency mismatch" in result.blocking_conditions


def test_knowledge_core_validation_blocks_prohibited_requests():
    validator = KnowledgeCoreValidation()

    result = validator.validate(
        KnowledgeCoreValidationRequest(
            **_valid_context(),
            detected_inconsistencies=("governance conflict",),
            use_corrupt_context_requested=True,
            ignore_roadmap_inconsistencies_requested=True,
            alter_governance_context_requested=True,
            overwrite_standards_requested=True,
            approve_invalid_dependencies_requested=True,
            hide_inconsistencies_requested=True,
            minimize_dependency_conflicts_requested=True,
            ignore_governance_issues_requested=True,
            alter_execution_history_requested=True,
        )
    )

    assert result.status == "blocked"
    assert "corrupt_context_usage_blocked" in result.reasons
    assert "roadmap_inconsistency_ignore_blocked" in result.reasons
    assert "governance_context_alteration_blocked" in result.reasons
    assert "standards_overwrite_blocked" in result.reasons
    assert "invalid_dependency_approval_blocked" in result.reasons
    assert "knowledge_inconsistency_concealment_blocked" in result.reasons
    assert "dependency_conflict_minimization_blocked" in result.reasons
    assert "governance_issue_ignore_blocked" in result.reasons
    assert "execution_history_alteration_blocked" in result.reasons


def test_knowledge_core_validation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    validator = KnowledgeCoreValidation(status=status)

    def broken_checks(*args, **kwargs):
        raise RuntimeError("knowledge validation exploded")

    monkeypatch.setattr(validator, "_checks", broken_checks)

    result = validator.validate(KnowledgeCoreValidationRequest(**_valid_context()))

    assert result.status == "error"
    assert "knowledge_core_validation_error_contained" in result.reasons

    metrics = status.knowledge_core_validation_metrics()
    assert metrics["knowledge_core_validation_status"] == "error"
    assert metrics["knowledge_core_validation_errors"] == 1
