"""
guardrails.py - Subfase 3.6.5
AI Operational Guardrails.
Valida prompts y responses. Bloquea comportamiento prohibido.
Claude es componente interno. Hermes mantiene TODO el control.
"""
import logging
import time

logger = logging.getLogger(__name__)

MAX_RESPONSE_CHARS = 4000

SYSTEM_PROMPT = """You are an internal operational component of Hermes, an autonomous task management system.

WHAT YOU ARE:
- An interpreter of operational context provided by Hermes
- A summarizer and analyzer of system state
- A proposer of observations based ONLY on received context

WHAT YOU ARE NOT:
- An autonomous agent
- A decision maker
- A planner with memory
- A system with database access
- A system that executes actions

STRICT RULES:
- Respond ONLY based on the context provided in this message
- Do NOT invent tasks, incidents, or metrics not present in the context
- Do NOT claim to have accessed any database
- Do NOT claim to have persistent memory
- Do NOT claim to have executed any action
- Do NOT create tasks autonomously
- Do NOT make final decisions
- Be brief, clear, and operational
- No corporate theater, no filler phrases

If you cannot answer based on the provided context, say exactly: "Insufficient context to respond."
"""

DANGEROUS_PATTERNS = [
    # English
    "i executed",
    "i accessed",
    "i stored",
    "i remembered",
    "i deployed",
    "i created",
    "i queried",
    "i connected",
    "i retrieved from",
    "i updated the",
    "i deleted",
    "i ran",
    "i checked the database",
    "i have memory",
    "i recall",
    # Spanish
    "ejecuté",
    "accedí",
    "consulté la db",
    "consulté la base",
    "consulté postgres",
    "guardé",
    "recordé",
    "recuerdo conversaciones",
    "desplegué",
    "creé una task",
    "creé la task",
    "tomé la decisión",
    "ejecuté una task",
    "analicé los logs completos",
    "tengo memoria",
]


class AIGuardrails:
    """
    Capa de control operacional para respuestas IA.
    Valida, limita y bloquea comportamiento prohibido.
    """

    def validate_response(self, response: str) -> dict:
        """
        Valida respuesta IA.
        Retorna contrato: safe, blocked, reason, response.
        """
        start = time.monotonic()

        if not response or not isinstance(response, str):
            return self._result(safe=False, blocked=True, reason="empty_or_invalid", response="")

        # Truncar si excede límite
        truncated = False
        if len(response) > MAX_RESPONSE_CHARS:
            response = response[:MAX_RESPONSE_CHARS]
            truncated = True
            logger.warning(
                "guardrails: response truncada a %d chars",
                MAX_RESPONSE_CHARS,
            )

        # Detectar patrones peligrosos
        response_lower = response.lower()
        for pattern in DANGEROUS_PATTERNS:
            if pattern in response_lower:
                duration_ms = int((time.monotonic() - start) * 1000)
                logger.warning(
                    "guardrails: response bloqueada patron='%s' chars=%d duration_ms=%d",
                    pattern,
                    len(response),
                    duration_ms,
                )
                return self._result(
                    safe=False,
                    blocked=True,
                    reason=f"dangerous_pattern: {pattern}",
                    response="Response blocked by guardrails",
                )

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "guardrails: response validada chars=%d truncated=%s duration_ms=%d",
            len(response),
            truncated,
            duration_ms,
        )

        return self._result(safe=True, blocked=False, reason=None, response=response)

    def get_system_prompt(self) -> str:
        """Retorna system prompt operacional fijo."""
        return SYSTEM_PROMPT

    def _result(self, safe: bool, blocked: bool, reason, response: str) -> dict:
        return {
            "safe": safe,
            "blocked": blocked,
            "reason": reason,
            "response": response,
        }


guardrails = AIGuardrails()