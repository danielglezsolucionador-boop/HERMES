"""
Controlled provider routing for Hermes runtime.

This layer selects the most appropriate AI provider for an execution request
using task complexity, cost, quality, health signals, and human constraints.
It does not call providers, change the active provider, retry, fallback
automatically, mutate tasks, or persist data.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.ai.provider_registry import provider_registry, setup_registry
from app.core.config import settings

logger = logging.getLogger(__name__)

ROUTING_TYPE_LOW_COST = "low_cost"
ROUTING_TYPE_STANDARD = "standard_execution"
ROUTING_TYPE_HIGH_REASONING = "high_reasoning"
ROUTING_TYPE_AUDIT = "audit"
SUPPORTED_ROUTING_TYPES = {
    ROUTING_TYPE_LOW_COST,
    ROUTING_TYPE_STANDARD,
    ROUTING_TYPE_HIGH_REASONING,
    ROUTING_TYPE_AUDIT,
}

ROUTING_STATUS_SELECTED = "selected"
ROUTING_STATUS_DEGRADED = "degraded"
ROUTING_STATUS_BLOCKED = "blocked"
ROUTING_STATUS_ERROR = "error"

COST_TIERS = {"low": 1, "standard": 2, "high": 3}
QUALITY_TIERS = {"basic": 1, "standard": 2, "high": 3}

PROVIDER_CATALOG = {
    "openrouter": {
        "cost_tier": "low",
        "quality_tier": "standard",
        "supported_routes": {
            ROUTING_TYPE_LOW_COST,
            ROUTING_TYPE_STANDARD,
            ROUTING_TYPE_AUDIT,
        },
    },
    "claude": {
        "cost_tier": "high",
        "quality_tier": "high",
        "supported_routes": {
            ROUTING_TYPE_STANDARD,
            ROUTING_TYPE_HIGH_REASONING,
            ROUTING_TYPE_AUDIT,
        },
    },
}


@dataclass(frozen=True)
class ProviderRoutingRequest:
    task_type: str = "operational_task"
    objective: str = ""
    prompt_type: str | None = None
    complexity: str = "standard"
    risk_level: str = "normal"
    output_type: str = ""
    runtime_requirements: tuple[str, ...] = field(default_factory=tuple)
    forced_provider: str | None = None
    blocked_providers: tuple[str, ...] = field(default_factory=tuple)
    max_cost_tier: str | None = None
    execution_priority: str | None = None
    available_providers: tuple[str, ...] = field(default_factory=tuple)
    provider_health: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderRoutingResult:
    status: str
    success: bool
    routing_id: str
    routing_type: str
    task_type: str
    provider_selected: str | None
    cost_estimate: str
    execution_priority: str
    routing_reason: str
    fallback_status: str
    fallback_provider: str | None = None
    provider_degraded: bool = False
    quality_estimate: str = "standard"
    execution_mode: str = "standard"
    runtime_limits: dict[str, Any] = field(default_factory=dict)
    available_providers: tuple[str, ...] = field(default_factory=tuple)
    blocked_providers: tuple[str, ...] = field(default_factory=tuple)
    evaluated_providers: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    selected_provider_health: dict[str, Any] = field(default_factory=dict)
    fallback_health: dict[str, Any] = field(default_factory=dict)
    routing_conflict: bool = False
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "routing_id": self.routing_id,
            "routing_type": self.routing_type,
            "task_type": self.task_type,
            "provider_selected": self.provider_selected,
            "cost_estimate": self.cost_estimate,
            "execution_priority": self.execution_priority,
            "routing_reason": self.routing_reason,
            "fallback_status": self.fallback_status,
            "fallback_provider": self.fallback_provider,
            "provider_degraded": self.provider_degraded,
            "quality_estimate": self.quality_estimate,
            "execution_mode": self.execution_mode,
            "runtime_limits": dict(self.runtime_limits),
            "available_providers": list(self.available_providers),
            "blocked_providers": list(self.blocked_providers),
            "evaluated_providers": [
                dict(provider) for provider in self.evaluated_providers
            ],
            "selected_provider_health": dict(self.selected_provider_health),
            "fallback_health": dict(self.fallback_health),
            "routing_conflict": self.routing_conflict,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "reasons": list(self.reasons),
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class ProviderRouting:
    def __init__(self, status: Any | None = None) -> None:
        self.status = status

    def decide(
        self,
        request: ProviderRoutingRequest,
        runtime_active: bool = True,
        routing_permitted: bool = True,
    ) -> ProviderRoutingResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        routing_id = str(uuid4())

        try:
            routing_type = self._routing_type(request)
            providers = self._providers(request)
            blocked = tuple(str(provider) for provider in request.blocked_providers)
            reasons = self._request_reasons(
                request=request,
                providers=providers,
                runtime_active=runtime_active,
                routing_permitted=routing_permitted,
            )
            evaluated = self._evaluate_providers(
                request=request,
                routing_type=routing_type,
                providers=providers,
                blocked=blocked,
            )
            selected = self._select_provider(
                request=request,
                evaluated=evaluated,
                reasons=reasons,
            )
            if reasons or selected is None:
                result = self._blocked_result(
                    request=request,
                    routing_id=routing_id,
                    routing_type=routing_type,
                    providers=providers,
                    blocked=blocked,
                    evaluated=evaluated,
                    reasons=reasons or ["no_routable_provider"],
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            fallback = self._fallback_provider(selected, evaluated)
            result = self._selected_result(
                request=request,
                routing_id=routing_id,
                routing_type=routing_type,
                selected=selected,
                fallback=fallback,
                providers=providers,
                blocked=blocked,
                evaluated=evaluated,
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._error_result(
                request=request,
                routing_id=routing_id,
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _request_reasons(
        self,
        request: ProviderRoutingRequest,
        providers: tuple[str, ...],
        runtime_active: bool,
        routing_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        blocked = set(request.blocked_providers)
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not routing_permitted:
            reasons.append("provider_routing_not_permitted")
        if not providers:
            reasons.append("no_providers_available")
        if request.forced_provider and request.forced_provider in blocked:
            reasons.append("forced_provider_blocked")
        if request.forced_provider and request.forced_provider not in providers:
            reasons.append("forced_provider_unavailable")
        max_cost = request.max_cost_tier
        if max_cost and max_cost not in COST_TIERS:
            reasons.append("invalid_max_cost_tier")
        return self._unique(reasons)

    def _providers(self, request: ProviderRoutingRequest) -> tuple[str, ...]:
        if request.available_providers:
            return tuple(self._unique([str(item) for item in request.available_providers]))
        if not provider_registry.available():
            setup_registry()
        return tuple(provider_registry.available())

    def _routing_type(self, request: ProviderRoutingRequest) -> str:
        requested = request.prompt_type or request.output_type
        if requested in SUPPORTED_ROUTING_TYPES:
            return str(requested)
        text = " ".join(
            [
                request.task_type,
                request.objective,
                request.prompt_type or "",
                request.output_type,
                request.complexity,
                request.risk_level,
                *request.runtime_requirements,
            ]
        ).lower()
        if self._has(text, ("audit", "qa", "review", "validation output")):
            return ROUTING_TYPE_AUDIT
        if (
            request.complexity.lower() in {"high", "complex"}
            or request.risk_level.lower() in {"high", "critical"}
            or self._has(text, ("architecture", "risk", "conflict", "advanced", "critical"))
        ):
            return ROUTING_TYPE_HIGH_REASONING
        if self._has(
            text,
            (
                "parsing",
                "formatting",
                "logging",
                "classification",
                "clasificacion",
                "simple",
            ),
        ):
            return ROUTING_TYPE_LOW_COST
        return ROUTING_TYPE_STANDARD

    def _evaluate_providers(
        self,
        request: ProviderRoutingRequest,
        routing_type: str,
        providers: tuple[str, ...],
        blocked: tuple[str, ...],
    ) -> tuple[dict[str, Any], ...]:
        evaluated = []
        max_cost = COST_TIERS.get(request.max_cost_tier or "high", 3)
        for provider in providers:
            catalog = self._catalog(provider)
            health = dict(request.provider_health.get(provider) or {})
            cost_value = COST_TIERS[catalog["cost_tier"]]
            blocked_provider = provider in blocked
            unavailable = self._unavailable(health)
            degraded = self._degraded(health)
            supports_route = routing_type in catalog["supported_routes"]
            cost_allowed = cost_value <= max_cost
            score = self._score(
                routing_type=routing_type,
                catalog=catalog,
                degraded=degraded,
                forced=provider == request.forced_provider,
            )
            reasons = []
            if blocked_provider:
                reasons.append("provider_blocked")
            if unavailable:
                reasons.append("provider_unavailable")
            if degraded:
                reasons.append("provider_degraded")
            if not supports_route:
                reasons.append("routing_type_not_preferred")
            if not cost_allowed:
                reasons.append("provider_cost_exceeds_limit")
            evaluated.append(
                {
                    "provider": provider,
                    "cost_tier": catalog["cost_tier"],
                    "quality_tier": catalog["quality_tier"],
                    "supports_route": supports_route,
                    "available": not unavailable,
                    "degraded": degraded,
                    "blocked": blocked_provider,
                    "cost_allowed": cost_allowed,
                    "score": score,
                    "health": health,
                    "reasons": reasons,
                }
            )
        return tuple(evaluated)

    def _select_provider(
        self,
        request: ProviderRoutingRequest,
        evaluated: tuple[dict[str, Any], ...],
        reasons: list[str],
    ) -> dict[str, Any] | None:
        if reasons:
            return None
        if request.forced_provider:
            forced = self._find(request.forced_provider, evaluated)
            if forced and forced["available"] and forced["cost_allowed"]:
                return forced
            return None
        candidates = [
            item
            for item in evaluated
            if item["available"] and not item["blocked"] and item["cost_allowed"]
        ]
        preferred = [item for item in candidates if item["supports_route"]]
        pool = preferred or candidates
        if not pool:
            return None
        return sorted(pool, key=lambda item: item["score"])[0]

    def _selected_result(
        self,
        request: ProviderRoutingRequest,
        routing_id: str,
        routing_type: str,
        selected: dict[str, Any],
        fallback: dict[str, Any] | None,
        providers: tuple[str, ...],
        blocked: tuple[str, ...],
        evaluated: tuple[dict[str, Any], ...],
        started: float,
        started_at: datetime,
    ) -> ProviderRoutingResult:
        provider_degraded = bool(selected["degraded"])
        return self._result(
            status=ROUTING_STATUS_DEGRADED if provider_degraded else ROUTING_STATUS_SELECTED,
            success=True,
            request=request,
            routing_id=routing_id,
            routing_type=routing_type,
            provider_selected=selected["provider"],
            cost_estimate=selected["cost_tier"],
            execution_priority=self._priority(request, routing_type),
            routing_reason=self._routing_reason(request, routing_type, selected),
            fallback_status=self._fallback_status(fallback),
            fallback_provider=fallback["provider"] if fallback else None,
            provider_degraded=provider_degraded,
            quality_estimate=selected["quality_tier"],
            execution_mode=routing_type,
            runtime_limits=self._runtime_limits(routing_type),
            available_providers=providers,
            blocked_providers=blocked,
            evaluated_providers=evaluated,
            selected_provider_health=selected["health"],
            fallback_health=fallback["health"] if fallback else {},
            reasons=list(selected["reasons"]),
            started=started,
            started_at=started_at,
        )

    def _blocked_result(
        self,
        request: ProviderRoutingRequest,
        routing_id: str,
        routing_type: str,
        providers: tuple[str, ...],
        blocked: tuple[str, ...],
        evaluated: tuple[dict[str, Any], ...],
        reasons: list[str],
        started: float,
        started_at: datetime,
    ) -> ProviderRoutingResult:
        return self._result(
            status=ROUTING_STATUS_BLOCKED,
            success=False,
            request=request,
            routing_id=routing_id,
            routing_type=routing_type,
            provider_selected=None,
            cost_estimate="blocked",
            execution_priority=self._priority(request, routing_type),
            routing_reason="routing blocked by safety controls",
            fallback_status="blocked",
            quality_estimate="blocked",
            execution_mode=routing_type,
            runtime_limits=self._runtime_limits(routing_type),
            available_providers=providers,
            blocked_providers=blocked,
            evaluated_providers=evaluated,
            routing_conflict=True,
            reasons=reasons,
            error=";".join(reasons),
            started=started,
            started_at=started_at,
        )

    def _error_result(
        self,
        request: ProviderRoutingRequest,
        routing_id: str,
        error: str,
        started: float,
        started_at: datetime,
    ) -> ProviderRoutingResult:
        return self._result(
            status=ROUTING_STATUS_ERROR,
            success=False,
            request=request,
            routing_id=routing_id,
            routing_type=ROUTING_TYPE_STANDARD,
            provider_selected=None,
            cost_estimate="unknown",
            execution_priority="blocked",
            routing_reason="provider routing error contained",
            fallback_status="blocked",
            quality_estimate="unknown",
            execution_mode=ROUTING_TYPE_STANDARD,
            routing_conflict=True,
            reasons=["provider_routing_error_contained"],
            error=error,
            started=started,
            started_at=started_at,
        )

    def _result(
        self,
        status: str,
        success: bool,
        request: ProviderRoutingRequest,
        routing_id: str,
        routing_type: str,
        provider_selected: str | None,
        cost_estimate: str,
        execution_priority: str,
        routing_reason: str,
        fallback_status: str,
        fallback_provider: str | None = None,
        provider_degraded: bool = False,
        quality_estimate: str = "standard",
        execution_mode: str = "standard",
        runtime_limits: dict[str, Any] | None = None,
        available_providers: tuple[str, ...] = (),
        blocked_providers: tuple[str, ...] = (),
        evaluated_providers: tuple[dict[str, Any], ...] = (),
        selected_provider_health: dict[str, Any] | None = None,
        fallback_health: dict[str, Any] | None = None,
        routing_conflict: bool = False,
        reasons: list[str] | None = None,
        error: str | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ProviderRoutingResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        return ProviderRoutingResult(
            status=status,
            success=success,
            routing_id=routing_id,
            routing_type=routing_type,
            task_type=request.task_type,
            provider_selected=provider_selected,
            cost_estimate=cost_estimate,
            execution_priority=execution_priority,
            routing_reason=routing_reason,
            fallback_status=fallback_status,
            fallback_provider=fallback_provider,
            provider_degraded=provider_degraded,
            quality_estimate=quality_estimate,
            execution_mode=execution_mode,
            runtime_limits=dict(runtime_limits or {}),
            available_providers=available_providers,
            blocked_providers=blocked_providers,
            evaluated_providers=evaluated_providers,
            selected_provider_health=dict(selected_provider_health or {}),
            fallback_health=dict(fallback_health or {}),
            routing_conflict=routing_conflict,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            reasons=tuple(reasons or []),
            error=error,
            metadata=dict(request.metadata),
        )

    def _catalog(self, provider: str) -> dict[str, Any]:
        catalog = PROVIDER_CATALOG.get(provider)
        if catalog:
            return {
                "cost_tier": catalog["cost_tier"],
                "quality_tier": catalog["quality_tier"],
                "supported_routes": set(catalog["supported_routes"]),
            }
        return {
            "cost_tier": "standard",
            "quality_tier": "standard",
            "supported_routes": set(SUPPORTED_ROUTING_TYPES),
        }

    def _score(
        self,
        routing_type: str,
        catalog: dict[str, Any],
        degraded: bool,
        forced: bool,
    ) -> int:
        cost = COST_TIERS[catalog["cost_tier"]]
        quality = QUALITY_TIERS[catalog["quality_tier"]]
        if routing_type == ROUTING_TYPE_LOW_COST:
            score = cost * 10 - quality
        elif routing_type in {ROUTING_TYPE_HIGH_REASONING, ROUTING_TYPE_AUDIT}:
            score = (4 - quality) * 10 + cost
        else:
            score = cost * 4 + (4 - quality) * 3
        if degraded:
            score += 50
        if forced:
            score -= 100
        return score

    def _fallback_provider(
        self,
        selected: dict[str, Any],
        evaluated: tuple[dict[str, Any], ...],
    ) -> dict[str, Any] | None:
        candidates = [
            item
            for item in evaluated
            if item["provider"] != selected["provider"]
            and item["available"]
            and not item["blocked"]
            and item["cost_allowed"]
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item["score"])[0]

    def _fallback_status(self, fallback: dict[str, Any] | None) -> str:
        if fallback is None:
            return "unavailable"
        if fallback["degraded"]:
            return "degraded_available"
        return "available"

    def _routing_reason(
        self,
        request: ProviderRoutingRequest,
        routing_type: str,
        selected: dict[str, Any],
    ) -> str:
        if request.forced_provider:
            return "provider forced by human control"
        if routing_type == ROUTING_TYPE_LOW_COST:
            return "low cost provider selected for simple operational work"
        if routing_type == ROUTING_TYPE_HIGH_REASONING:
            return "high quality provider selected for high-risk reasoning"
        if routing_type == ROUTING_TYPE_AUDIT:
            return "audit-capable provider selected for validation"
        if selected["degraded"]:
            return "provider selected with degradation visible"
        return "standard provider selected for balanced execution"

    def _priority(self, request: ProviderRoutingRequest, routing_type: str) -> str:
        if request.execution_priority:
            return request.execution_priority
        if request.risk_level.lower() == "critical":
            return "critical"
        if routing_type in {ROUTING_TYPE_HIGH_REASONING, ROUTING_TYPE_AUDIT}:
            return "high"
        if routing_type == ROUTING_TYPE_LOW_COST:
            return "low"
        return "standard"

    def _runtime_limits(self, routing_type: str) -> dict[str, Any]:
        max_tokens = settings.PROVIDER_BRIDGE_MAX_TOKENS
        if routing_type == ROUTING_TYPE_LOW_COST:
            tokens = min(512, max_tokens)
        elif routing_type == ROUTING_TYPE_HIGH_REASONING:
            tokens = max_tokens
        else:
            tokens = min(1024, max_tokens)
        return {
            "max_tokens": tokens,
            "timeout_seconds": settings.PROVIDER_BRIDGE_TIMEOUT_SECONDS,
            "max_request_bytes": settings.PROVIDER_BRIDGE_MAX_REQUEST_BYTES,
            "max_response_bytes": settings.PROVIDER_BRIDGE_MAX_RESPONSE_BYTES,
            "max_concurrent_provider_calls": (
                settings.PROVIDER_BRIDGE_MAX_CONCURRENT_CALLS
            ),
        }

    def _unavailable(self, health: dict[str, Any]) -> bool:
        if not health:
            return False
        if health.get("configured") is False:
            return True
        return health.get("available") is False

    def _degraded(self, health: dict[str, Any]) -> bool:
        if not health:
            return False
        if health.get("degraded") is True:
            return True
        error_rate = self._float(health.get("error_rate"))
        avg_duration = self._float(health.get("avg_duration_ms"))
        return error_rate > 0.2 or avg_duration > 15000

    def _find(
        self,
        provider: str,
        evaluated: tuple[dict[str, Any], ...],
    ) -> dict[str, Any] | None:
        for item in evaluated:
            if item["provider"] == provider:
                return item
        return None

    def _float(self, value: Any) -> float:
        try:
            return max(0.0, float(value or 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _has(self, text: str, needles: tuple[str, ...]) -> bool:
        return any(needle in text for needle in needles)

    def _unique(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _publish(self, result: ProviderRoutingResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_provider_routing_result",
        ):
            self.status.mark_provider_routing_result(result.to_dict())

    def _log_result(self, result: ProviderRoutingResult) -> None:
        if result.success:
            logger.info(
                "provider_routing: selected routing_id=%s provider=%s type=%s cost=%s fallback=%s",
                result.routing_id,
                result.provider_selected,
                result.routing_type,
                result.cost_estimate,
                result.fallback_status,
            )
            return
        logger.warning(
            "provider_routing: blocked routing_id=%s type=%s reasons=%s error=%s",
            result.routing_id,
            result.routing_type,
            ",".join(result.reasons),
            result.error,
        )
