"""
openrouter_provider.py - Subfase 3.7.1
OpenRouter provider para Hermes.
Implementa AIProvider. Compatible con OpenAI API format.
Permite acceso a DeepSeek, Llama, Mistral y otros modelos baratos/gratis.
"""
import asyncio
import logging
import time
import httpx
from app.ai.providers.base import AIProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEFAULT_MODEL = "deepseek/deepseek-chat"
OPENROUTER_TIMEOUT = 30


def _is_configured() -> bool:
    return bool(settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip())


class OpenRouterProvider(AIProvider):
    """
    Provider OpenRouter para Hermes.
    Soporta DeepSeek, Llama, Mistral y otros via API unificada.
    """

    @property
    def provider_name(self) -> str:
        return "openrouter"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        """Genera respuesta usando OpenRouter API."""
        if not _is_configured():
            logger.warning("openrouter: request bloqueada — OPENROUTER_API_KEY no configurada")
            return self._error("auth_failed", "OPENROUTER_API_KEY no configurada", 0)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hermes.internal",
            "X-Title": "Hermes",
        }
        body = {
            "model": OPENROUTER_DEFAULT_MODEL,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        start_ms = time.monotonic()
        logger.info(
            "openrouter: request iniciada model=%s max_tokens=%d",
            OPENROUTER_DEFAULT_MODEL, max_tokens,
        )

        try:
            async with httpx.AsyncClient(timeout=OPENROUTER_TIMEOUT) as client:
                response = await client.post(OPENROUTER_API_URL, headers=headers, json=body)

            duration_ms = int((time.monotonic() - start_ms) * 1000)

            if response.status_code == 401:
                logger.error("openrouter: auth_failed status=401 duration_ms=%d", duration_ms)
                return self._error("auth_failed", "API key invalida o sin permisos", duration_ms)

            if response.status_code == 429:
                logger.warning("openrouter: rate_limited status=429 duration_ms=%d", duration_ms)
                return self._error("rate_limited", "Rate limit alcanzado", duration_ms)

            if response.status_code != 200:
                logger.error("openrouter: provider_error status=%d duration_ms=%d", response.status_code, duration_ms)
                return self._error("provider_error", f"HTTP {response.status_code}", duration_ms)

            data = response.json()
            choices = data.get("choices", [])
            if not choices or not choices[0].get("message", {}).get("content"):
                logger.error("openrouter: invalid_response — sin content duration_ms=%d", duration_ms)
                return self._error("invalid_response", "Respuesta sin content", duration_ms)

            content = choices[0]["message"]["content"]
            usage = data.get("usage", {})
            model = data.get("model", OPENROUTER_DEFAULT_MODEL)

            logger.info(
                "openrouter: completado model=%s input_tokens=%d output_tokens=%d duration_ms=%d",
                model,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                duration_ms,
            )

            return {
                "success": True,
                "content": content,
                "model": model,
                "usage": {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                },
                "duration_ms": duration_ms,
                "error": None,
                "error_type": None,
            }

        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            logger.error("openrouter: timeout despues de %ds duration_ms=%d", OPENROUTER_TIMEOUT, duration_ms)
            return self._error("timeout", f"Timeout despues de {OPENROUTER_TIMEOUT}s", duration_ms)

        except httpx.ConnectError as exc:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            logger.error("openrouter: connect_error=%s duration_ms=%d", exc, duration_ms)
            return self._error("provider_error", "No se pudo conectar a OpenRouter", duration_ms)

        except Exception as exc:
            duration_ms = int((time.monotonic() - start_ms) * 1000)
            logger.error("openrouter: error inesperado=%s duration_ms=%d", exc, duration_ms)
            return self._error("provider_error", str(exc), duration_ms)

    async def healthcheck(self) -> dict:
        """Verifica estado del provider OpenRouter."""
        configured = _is_configured()
        return {
            "available": configured,
            "configured": configured,
            "last_error": None if configured else "OPENROUTER_API_KEY no configurada",
            "timeout_support": True,
        }

    def _error(self, error_type: str, error: str, duration_ms: int) -> dict:
        return {
            "success": False,
            "content": "",
            "model": OPENROUTER_DEFAULT_MODEL,
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "duration_ms": duration_ms,
            "error": error,
            "error_type": error_type,
        }