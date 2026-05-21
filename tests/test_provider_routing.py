from app.runner.provider_routing import ProviderRouting, ProviderRoutingRequest
from app.services.runtime_status import RuntimeStatus


AVAILABLE = ("openrouter", "claude")
HEALTHY = {
    "openrouter": {"available": True, "configured": True, "error_rate": 0.0},
    "claude": {"available": True, "configured": True, "error_rate": 0.0},
}


def test_provider_routing_selects_low_cost_provider_for_simple_task():
    status = RuntimeStatus()
    routing = ProviderRouting(status=status)

    result = routing.decide(
        ProviderRoutingRequest(
            task_type="parsing",
            objective="format operational logs",
            complexity="low",
            available_providers=AVAILABLE,
            provider_health=HEALTHY,
            metadata={"phase": "5.2.5"},
        )
    )

    assert result.status == "selected"
    assert result.routing_type == "low_cost"
    assert result.provider_selected == "openrouter"
    assert result.cost_estimate == "low"
    assert result.execution_priority == "low"
    assert result.fallback_status == "available"
    assert result.runtime_limits["max_tokens"] <= 512

    metrics = status.provider_routing_metrics()
    assert metrics["provider_routing_status"] == "selected"
    assert metrics["provider_routes_selected"] == 1
    assert metrics["provider_selected"] == "openrouter"


def test_provider_routing_selects_high_reasoning_provider_when_healthy():
    routing = ProviderRouting()

    result = routing.decide(
        ProviderRoutingRequest(
            task_type="architecture",
            objective="detect runtime conflict risk",
            complexity="high",
            risk_level="critical",
            runtime_requirements=("advanced validation",),
            available_providers=AVAILABLE,
            provider_health=HEALTHY,
        )
    )

    assert result.status == "selected"
    assert result.routing_type == "high_reasoning"
    assert result.provider_selected == "claude"
    assert result.cost_estimate == "high"
    assert result.quality_estimate == "high"
    assert result.execution_priority == "critical"


def test_provider_routing_keeps_forced_degraded_provider_visible_with_fallback():
    routing = ProviderRouting()
    health = {
        "openrouter": {
            "available": True,
            "configured": True,
            "degraded": True,
            "error_rate": 0.4,
        },
        "claude": {"available": True, "configured": True, "error_rate": 0.0},
    }

    result = routing.decide(
        ProviderRoutingRequest(
            task_type="standard workflow",
            forced_provider="openrouter",
            available_providers=AVAILABLE,
            provider_health=health,
        )
    )

    assert result.status == "degraded"
    assert result.provider_selected == "openrouter"
    assert result.provider_degraded is True
    assert result.fallback_provider == "claude"
    assert result.fallback_status == "available"
    assert "provider_degraded" in result.reasons


def test_provider_routing_blocks_forced_blocked_provider():
    routing = ProviderRouting()

    result = routing.decide(
        ProviderRoutingRequest(
            task_type="standard workflow",
            forced_provider="openrouter",
            blocked_providers=("openrouter",),
            available_providers=AVAILABLE,
            provider_health=HEALTHY,
        )
    )

    assert result.status == "blocked"
    assert result.success is False
    assert result.provider_selected is None
    assert result.routing_conflict is True
    assert "forced_provider_blocked" in result.reasons


def test_provider_routing_respects_cost_limit_without_low_quality_forced_selection():
    routing = ProviderRouting()

    result = routing.decide(
        ProviderRoutingRequest(
            task_type="validation",
            objective="advanced audit review",
            prompt_type="audit",
            max_cost_tier="low",
            available_providers=AVAILABLE,
            provider_health=HEALTHY,
        )
    )

    assert result.status == "selected"
    assert result.routing_type == "audit"
    assert result.provider_selected == "openrouter"
    assert result.cost_estimate == "low"
    assert result.fallback_status == "unavailable"


def test_provider_routing_contains_internal_errors(monkeypatch):
    routing = ProviderRouting()

    def broken_providers(request):
        raise RuntimeError("routing context exploded")

    monkeypatch.setattr(routing, "_providers", broken_providers)

    result = routing.decide(ProviderRoutingRequest())

    assert result.status == "error"
    assert result.success is False
    assert result.routing_conflict is True
    assert "provider_routing_error_contained" in result.reasons
