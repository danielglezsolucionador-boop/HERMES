"""
telegram_bridge.py - Subfase 3.6.6
Telegram AI Bridge.
Pipeline controlado: query -> orchestrator -> guardrails -> respuesta segura.
Claude NO ejecuta acciones. Claude SOLO responde con contexto construido por Hermes.
"""
import logging
import time
import asyncio
from app.ai.orchestrator import orchestrator
from app.services.operational_memory import (
    build_memory_augmented_prompt,
    maybe_handle_memory_query,
)
from app.services.operational_summary import maybe_handle_operational_query

logger = logging.getLogger(__name__)

MAX_BRIDGE_SECONDS = 25


class TelegramAIBridge:
    """
    Bridge controlado entre Telegram y el pipeline IA de Hermes.
    Maneja timeouts, errores y formato de respuesta.
    """

    async def handle_query(self, query: str) -> str:
        """
        Recibe query de Telegram, llama orchestrator, retorna respuesta segura.
        Nunca rompe polling ni FastAPI.
        """
        start = time.monotonic()
        query_chars = len(query)
        logger.info("telegram_bridge: query recibida chars=%d", query_chars)

        operational_response = await maybe_handle_operational_query(query)
        if operational_response:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("telegram_bridge: respuesta operacional duration_ms=%d", duration_ms)
            return self._format_operational(operational_response)

        memory_response = await maybe_handle_memory_query(query)
        if memory_response:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("telegram_bridge: respuesta memoria duration_ms=%d", duration_ms)
            return self._format_operational(memory_response)

        ai_query = await build_memory_augmented_prompt(query)

        try:
            result = await asyncio.wait_for(
                orchestrator.generate(ai_query),
                timeout=MAX_BRIDGE_SECONDS,
            )
        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "telegram_bridge: timeout duration_ms=%d", duration_ms
            )
            return "AI timeout"

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "telegram_bridge: error inesperado=%s duration_ms=%d", exc, duration_ms
            )
            return "AI provider unavailable"

        duration_ms = int((time.monotonic() - start) * 1000)

        if not result.get("success"):
            logger.warning(
                "telegram_bridge: provider error=%s duration_ms=%d",
                result.get("error"), duration_ms,
            )
            return "AI provider unavailable"

        response = result.get("response") or ""

        if result.get("guardrail_blocked"):
            logger.warning(
                "telegram_bridge: guardrail bloqueo reason=%s duration_ms=%d",
                result.get("guardrail_reason"), duration_ms,
            )

        logger.info(
            "telegram_bridge: completado chars=%d duration_ms=%d blocked=%s",
            len(response), duration_ms, result.get("guardrail_blocked", False),
        )

        return self._format(response)

    def _format(self, response: str) -> str:
        """Formatea respuesta para Telegram."""
        if not response:
            return "AI provider unavailable"
        return f"🤖 Hermes AI\n\n{response}"

    def _format_operational(self, response: str) -> str:
        if not response:
            return "Hermes operacional\n\nSin datos operacionales disponibles."
        return f"Hermes operacional\n\n{response}"


telegram_ai_bridge = TelegramAIBridge()
