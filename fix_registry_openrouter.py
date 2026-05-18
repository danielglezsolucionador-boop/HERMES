path = r"app\ai\provider_registry.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_setup = '''def setup_registry(active_provider: str = "claude") -> None:
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
    )'''

new_setup = '''def setup_registry(active_provider: str | None = None) -> None:
    """
    Inicializa el registry con los providers disponibles.
    Usa AI_PROVIDER de config si no se especifica activo.
    Llamar en startup de Hermes.
    """
    from app.core.config import settings
    from app.ai.providers.claude_provider import ClaudeProvider
    from app.ai.providers.openrouter_provider import OpenRouterProvider

    provider_registry.register(ClaudeProvider())
    provider_registry.register(OpenRouterProvider())

    active = active_provider or settings.AI_PROVIDER or "openrouter"

    try:
        provider_registry.set_active(active)
    except ValueError:
        logger.error(
            "provider_registry: provider '%s' no disponible, usando openrouter por defecto", active
        )
        provider_registry.set_active("openrouter")

    logger.info(
        "provider_registry: setup completo providers=%s active='%s'",
        provider_registry.available(),
        provider_registry.active_name(),
    )'''

assert old_setup in content, "ERROR: setup_registry no encontrado"
content = content.replace(old_setup, new_setup, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — provider_registry.py actualizado con OpenRouterProvider")