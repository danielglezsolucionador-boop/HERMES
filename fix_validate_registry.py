import asyncio
from app.ai.provider_registry import provider_registry, setup_registry
from app.ai.providers.claude_provider import ClaudeProvider

async def main():
    # Caso 1: setup registry
    setup_registry()
    print("CASO 1 setup:", provider_registry.active_name(), provider_registry.available())

    # Caso 2: get_active retorna ClaudeProvider
    provider = provider_registry.get_active()
    assert isinstance(provider, ClaudeProvider), "ERROR: provider incorrecto"
    print("CASO 2 get_active:", provider.provider_name)

    # Caso 3: healthcheck
    health = await provider.healthcheck()
    print("CASO 3 healthcheck:", health)

    # Caso 4: provider inexistente retorna None
    p = provider_registry.get("deepseek")
    assert p is None, "ERROR: deberia ser None"
    print("CASO 4 get inexistente: None OK")

    # Caso 5: set_active inexistente lanza error
    try:
        provider_registry.set_active("openai")
        print("CASO 5 ERROR: debio lanzar excepcion")
    except ValueError as e:
        print("CASO 5 set_active invalido: OK", e)

    print("--- TODOS LOS CASOS OK ---")

asyncio.run(main())