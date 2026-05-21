from app.runner.preference_adaptation import (
    PreferenceAdaptation,
    PreferenceAdaptationRequest,
)
from app.services.runtime_status import RuntimeStatus


def test_preference_adaptation_detects_communication_preferences_and_metrics():
    status = RuntimeStatus()
    adaptation = PreferenceAdaptation(status=status)

    result = adaptation.adapt(
        PreferenceAdaptationRequest(
            preference_type="communication",
            human_context={
                "tone": "direct",
                "clarity": "high",
                "technical_level": "operational",
            },
            interaction_history=(
                {"tone": "direct", "interaction_format": "handoff"},
                {"clarity": "high", "technical_level": "operational"},
            ),
            governance_status="approved",
            validation_status="validated",
            runtime_state={"state": "active"},
        )
    )

    assert result.status == "adapted"
    assert result.success is True
    assert result.human_authority_preserved is True
    assert result.transparency_preserved is True
    assert result.application_status == "suggested_only"
    assert result.communication_adjustments

    metrics = status.preference_adaptation_metrics()
    assert metrics["preference_adaptation_status"] == "adapted"
    assert metrics["preference_adaptations_learned"] == 1
    assert metrics["preferences_detected_count"] >= 3
    assert metrics["human_authority_preserved"] is True


def test_preference_adaptation_applies_only_after_governance_validation_and_runtime_safety():
    adaptation = PreferenceAdaptation()

    result = adaptation.adapt(
        PreferenceAdaptationRequest(
            preference_type="reporting",
            human_context={
                "detail_level": "concise",
                "report_format": "operational_handoff",
            },
            reporting_feedback=(
                {"detail_level": "concise"},
                {"report_format": "operational_handoff"},
            ),
            governance_status="human_approved",
            validation_status="validated",
            runtime_state={"loop_state": "active"},
            application_requested=True,
        )
    )

    assert result.status == "adapted"
    assert result.application_status == "applied"
    assert result.governance_compliant is True
    assert result.validation_consistent is True
    assert result.operational_safe is True


def test_preference_adaptation_blocks_application_without_governance():
    adaptation = PreferenceAdaptation()

    result = adaptation.adapt(
        PreferenceAdaptationRequest(
            preference_type="workflow",
            workflow_preferences=({"workflow": "phase_order"},),
            governance_status="rejected",
            validation_status="validated",
            runtime_state={"state": "active"},
            application_requested=True,
        )
    )

    assert result.status == "blocked"
    assert result.governance_compliant is False
    assert "governance_approval_required_for_application" in result.reasons


def test_preference_adaptation_blocks_manipulation_and_psychological_profile():
    adaptation = PreferenceAdaptation()

    result = adaptation.adapt(
        PreferenceAdaptationRequest(
            preference_type="communication",
            human_context={"tone": "direct"},
            manipulation_requested=True,
            psychological_profile_requested=True,
            metadata={"intent": "create dependency and modify objective"},
        )
    )

    assert result.status == "blocked"
    assert "manipulation_blocked" in result.reasons
    assert "psychological_profile_blocked" in result.reasons
    assert "dependency_creation_blocked" in result.reasons
    assert "objective_modification_blocked" in result.reasons
    assert result.context_safe is False


def test_preference_adaptation_blocks_human_authority_override():
    adaptation = PreferenceAdaptation()

    result = adaptation.adapt(
        PreferenceAdaptationRequest(
            preference_type="governance",
            governance_status="approved",
            allow_governance_change=True,
            assume_strategic_authority=True,
        )
    )

    assert result.status == "blocked"
    assert "governance_change_blocked" in result.reasons
    assert "human_authority_override_blocked" in result.reasons
    assert result.human_authority_preserved is False


def test_preference_adaptation_reports_no_preferences_without_signals():
    adaptation = PreferenceAdaptation()

    result = adaptation.analyze(
        PreferenceAdaptationRequest(preference_type="execution")
    )

    assert result.status == "no_preferences"
    assert result.success is True
    assert result.preferences_detected == ()
    assert result.application_status == "not_available"


def test_preference_adaptation_contains_internal_errors(monkeypatch):
    status = RuntimeStatus()
    adaptation = PreferenceAdaptation(status=status)

    def broken_detection(*args, **kwargs):
        raise RuntimeError("preference detector exploded")

    monkeypatch.setattr(adaptation, "_detect_preferences", broken_detection)

    result = adaptation.adapt(
        PreferenceAdaptationRequest(
            preference_type="communication",
            human_context={"tone": "direct"},
        )
    )

    assert result.status == "error"
    assert result.success is False
    assert "preference_adaptation_error_contained" in result.reasons
    metrics = status.preference_adaptation_metrics()
    assert metrics["preference_adaptation_errors"] == 1
