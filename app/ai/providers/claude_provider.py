"""
claude_provider.py - Subfase 3.6.7
Claude (Anthropic) provider para Hermes.
Implementa AIProvider. Wrapper sobre claude_client existente.
NO rompe compatibilidad con orchestrator actual.
"""
import logging
from app.ai.providers.base import AIProvider
from app.integrations.claude_client import ask, _is_configured

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    """
    Provider Anthropic Claude.
    Delega en claude_client.py existente — sin duplicar lógica.
    """

    @property
    def provider_name(self) -> str:
        return "claude"

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        """Genera respuesta usando Claude API."""
        return await ask(prompt, max_tokens=max_tokens, system_prompt=system_prompt)

    async def healthcheck(self) -> dict:
        """Verifica estado del provider Claude."""
        configured = _is_configured()
        return {
            "available": configured,
            "configured": configured,
            "last_error": None if configured else "CLAUDE_API_KEY no configurada",
            "timeout_support": True,
        }