"""
Controlled AI orchestrator.
Pipeline: context_builder -> provider_registry -> provider -> guardrails.
"""
import asyncio
import json
import logging
import time

from app.ai.context_builder import build_context
from app.ai.context_isolation import sanitize_text
from app.ai.guardrails import guardrails
from app.ai.provider_registry import provider_registry, setup_registry

logger = logging.getLogger(__name__)

MAX_AI_SECONDS = 25


def _build_prompt(context: dict, user_prompt: str) -> str:
    safe_user_prompt = sanitize_text(user_prompt, max_chars=2000)
    safe_context = {
        "summary": context.get("summary"),
        "tasks": context.get("tasks", []),
        "incidents": context.get("incidents", []),
        "metadata": context.get("metadata", {}),
    }
    return "\n".join(
        [
            "HERMES OPERATIONAL CONTEXT",
            json.dumps(safe_context, ensure_ascii=False, default=str),
            "",
            "USER REQUEST",
            safe_user_prompt,
        ]
    )


class AIResponseOrchestrator:
    async def generate(self, user_prompt: str, max_tokens: int = 1024) -> dict:
        start = time.monotonic()
        try:
            return await asyncio.wait_for(
                self._pipeline(user_prompt=user_prompt, max_tokens=max_tokens),
                timeout=MAX_AI_SECONDS,
            )
        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("orchestrator: timeout duration_ms=%s", duration_ms)
            return self._error("timeout", f"AI timeout after {MAX_AI_SECONDS}s", duration_ms)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("orchestrator: unexpected error=%s duration_ms=%s", exc, duration_ms)
            return self._error("provider_error", str(exc), duration_ms)

    async def _pipeline(self, user_prompt: str, max_tokens: int) -> dict:
        start = time.monotonic()
        if provider_registry.active_name() is None:
            setup_registry()

        provider = provider_registry.get_active()
        health = await provider.healthcheck()
        if not health.get("configured"):
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "orchestrator: provider not configured provider=%s",
                provider.provider_name,
            )
            return self._error(
                "auth_failed",
                health.get("last_error") or "Provider no configurado",
                duration_ms,
                provider=provider.provider_name,
                configured=False,
            )

        context = await build_context()
        full_prompt = _build_prompt(context, user_prompt)
        provider_result = await provider.generate(
            full_prompt,
            system_prompt=guardrails.get_system_prompt(),
            max_tokens=max_tokens,
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        if not provider_result.get("success"):
            return self._error(
                provider_result.get("error_type") or "provider_error",
                provider_result.get("error") or "Provider error",
                duration_ms,
                provider=provider.provider_name,
                model=provider_result.get("model"),
                configured=True,
            )

        guardrail_result = guardrails.validate_response(provider_result.get("content", ""))
        response = guardrail_result.get("response", "")
        success = bool(guardrail_result.get("safe")) and not guardrail_result.get("blocked")
        usage = provider_result.get("usage", {})

        return {
            "success": success,
            "response": response,
            "provider": provider.provider_name,
            "model": provider_result.get("model"),
            "duration_ms": duration_ms,
            "provider_ms": provider_result.get("duration_ms", 0),
            "usage": usage,
            "tokens_estimated": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "context_chars": context.get("_timing", {}).get("chars", 0),
            "guardrail_blocked": guardrail_result.get("blocked", False),
            "guardrail_reason": guardrail_result.get("reason"),
            "handoff": {
                "agent": provider.provider_name,
                "status": "completed" if success else "blocked",
                "model": provider_result.get("model"),
                "duration_ms": duration_ms,
            },
            "error": None if success else guardrail_result.get("reason"),
        }

    def _error(
        self,
        error_type: str,
        error: str,
        duration_ms: int,
        provider: str | None = None,
        model: str | None = None,
        configured: bool | None = None,
    ) -> dict:
        return {
            "success": False,
            "response": None,
            "provider": provider or provider_registry.active_name(),
            "model": model,
            "duration_ms": duration_ms,
            "provider_ms": 0,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "tokens_estimated": 0,
            "context_chars": 0,
            "guardrail_blocked": False,
            "guardrail_reason": None,
            "handoff": {
                "agent": provider or provider_registry.active_name(),
                "status": "failed",
                "model": model,
                "duration_ms": duration_ms,
                "configured": configured,
            },
            "error": error_type,
            "error_detail": error,
        }


orchestrator = AIResponseOrchestrator()
