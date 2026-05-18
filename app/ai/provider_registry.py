"""
provider_registry.py - Subfase 3.6.7
Registry de providers IA de Hermes.
Registra, obtiene y valida providers disponibles.
Hermes NO está acoplado a ningún provider específico.
"""
import logging
from app.ai.providers.base import AIProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registro central de providers IA.
    Permite agregar providers y obtener el activo por nombre.
    """

    def __init__(self):
        self._providers: dict[str, AIProvider] = {}
        self._active: str | None = None

    def register(self, provider: AIProvider) -> None:
        """Registra un provider en el registry."""
        name = provider.provider_name
        self._providers[name] = provider
        logger.info("provider_registry: registrado provider='%s'", name)

    def set_active(self, name: str) -> None:
        """Define el provider activo por nombre."""
        if name not in self._providers:
            logger.error("provider_registry: provider '%s' no registrado", name)
            raise ValueError(f"Provider '{name}' no registrado")
        self._active = name
        logger.info("provider_registry: provider activo='%s'", name)

    def get_active(self) -> AIProvider:
        """Retorna el provider activo. Falla explícito si no hay ninguno."""
        if self._active is None or self._active not in self._providers:
            raise RuntimeError("No hay provider activo configurado en Hermes")
        return self._providers[self._active]

    def get(self, name: str) -> AIProvider | None:
        """Obtiene provider por nombre. Retorna None si no existe."""
        return self._providers.get(name)

    def available(self) -> list[str]:
        """Lista nombres de providers registrados."""
        return list(self._providers.keys())

    def active_name(self) -> str | None:
        """Nombre del provider activo."""
        return self._active


# Instancia global
provider_registry = ProviderRegistry()


def setup_registry(active_provider: str = "claude") -> None:
    """
    Inicializa el registry con los providers disponibles.
    Llamar en startup de Hermes.
    """
    from app.ai.providers.claude_provider import ClaudeProvider
    provider_registry.register(ClaudeProvider())
    provider_registry.set_active(active_provider)
    logger.info(
        "provider_registry: setup completo providers=%s active='%s'",
        provider_registry.available(),
        active_provider,
    )