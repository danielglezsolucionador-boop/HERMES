"""
Safe Claude API client.
This module is isolated from tasks, Telegram, and runner state.
"""
import asyncio
import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
CLAUDE_TIMEOUT = 30


def _is_configured() -> bool:
    return bool(settings.CLAUDE_API_KEY and settings.CLAUDE_API_KEY.strip())


def validate_startup() -> None:
    if not _is_configured():
        logger.warning(
            "claude_client: provider_not_configured CLAUDE_API_KEY missing; "
            "AI infrastructure disabled safely"
        )
        return
    if not settings.CLAUDE_REAL_REQUESTS_ENABLED:
        logger.warning(
            "claude_client: provider_configured_but_disabled; "
            "real Claude requests are blocked for infrastructure-only validation"
        )
        return
    logger.info("claude_client: configured and real requests enabled")


def _error(
    error_type: str,
    error: str,
    duration_ms: int,
    model: str | None = CLAUDE_MODEL,
) -> dict:
    return {
        "success": False,
        "content": None,
        "model": model,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "duration_ms": duration_ms,
        "error": error,
        "error_type": error_type,
    }


async def ask(
    prompt: str,
    max_tokens: int = 1024,
    system_prompt: str | None = None,
) -> dict:
    """Send a prompt to Claude and return the normalized provider contract."""
    if not _is_configured():
        logger.warning("claude_client: blocked request, provider_not_configured")
        return _error(
            "provider_not_configured",
            "provider_not_configured",
            0,
            model=None,
        )

    if not settings.CLAUDE_REAL_REQUESTS_ENABLED:
        logger.warning("claude_client: blocked request, provider_disabled")
        return _error(
            "provider_disabled",
            "provider_disabled",
            0,
            model=None,
        )

    headers = {
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        body["system"] = system_prompt

    start = time.monotonic()
    logger.info("claude_client: request started model=%s", CLAUDE_MODEL)

    try:
        async with httpx.AsyncClient(timeout=CLAUDE_TIMEOUT) as client:
            response = await client.post(CLAUDE_API_URL, headers=headers, json=body)

        duration_ms = int((time.monotonic() - start) * 1000)
        if response.status_code == 401:
            return _error("auth_failed", "API key invalida o sin permisos", duration_ms)
        if response.status_code == 429:
            return _error("rate_limited", "Rate limit alcanzado", duration_ms)
        if response.status_code != 200:
            logger.error("claude_client: provider HTTP %s", response.status_code)
            return _error("provider_error", f"HTTP {response.status_code}", duration_ms)

        data = response.json()
        blocks = data.get("content", [])
        text = ""
        if blocks and isinstance(blocks, list):
            text = "\n".join(
                block.get("text", "")
                for block in blocks
                if block.get("type") == "text"
            ).strip()
        if not text:
            return _error("invalid_response", "Respuesta sin texto", duration_ms)

        usage = data.get("usage", {})
        model = data.get("model", CLAUDE_MODEL)
        logger.info(
            "claude_client: completed model=%s input_tokens=%s output_tokens=%s duration_ms=%s",
            model,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            duration_ms,
        )
        return {
            "success": True,
            "content": text,
            "model": model,
            "usage": {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            "duration_ms": duration_ms,
            "error": None,
            "error_type": None,
        }
    except asyncio.TimeoutError:
        duration_ms = int((time.monotonic() - start) * 1000)
        return _error("timeout", f"Timeout despues de {CLAUDE_TIMEOUT}s", duration_ms)
    except httpx.TimeoutException:
        duration_ms = int((time.monotonic() - start) * 1000)
        return _error("timeout", f"Timeout despues de {CLAUDE_TIMEOUT}s", duration_ms)
    except httpx.ConnectError:
        duration_ms = int((time.monotonic() - start) * 1000)
        return _error("provider_error", "No se pudo conectar a Claude", duration_ms)
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.error("claude_client: unexpected error=%s", exc)
        return _error("provider_error", str(exc), duration_ms)
