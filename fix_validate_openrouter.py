import asyncio
from app.ai.provider_registry import provider_registry, setup_registry
from app.ai.providers.openrouter_provider import OpenRouterProvider

async def main():
    # Caso 1: setup con ambos providers
    setup_registry()
    print("CASO 1 setup:", provider_registry.active_name(), provider_registry.available())

    # Caso 2: provider activo es OpenRouterProvider
    provider = provider_registry.get_active()
    assert isinstance(provider, OpenRouterProvider), "ERROR: tipo incorrecto"
    print("CASO 2 get_active:", provider.provider_name)

    # Caso 3: healthcheck
    health = await provider.healthcheck()
    print("CASO 3 healthcheck:", health)

    # Caso 4: ClaudeProvider sigue disponible
    claude = provider_registry.get("claude")
    assert claude is not None, "ERROR: claude no disponible"
    print("CASO 4 claude disponible:", claude.provider_name)

    print("--- TODOS LOS CASOS OK ---")

asyncio.run(main())