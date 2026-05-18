import asyncio
from app.ai.provider_registry import provider_registry, setup_registry
from app.ai.providers.claude_provider import ClaudeProvider

async def main():
    # Caso 1: setup_registry inicializa correctamente
    setup_registry()
    print("CASO 1 setup:", provider_registry.active_name(), provider_registry.available())

    # Caso 2: get_active retorna ClaudeProvider
    provider = provider_registry.get_active()
    assert isinstance(provider, ClaudeProvider), "ERROR: tipo incorrecto"
    print("CASO 2 get_active:", provider.provider_name)

    # Caso 3: healthcheck sin API key — configured=False
    health = await provider.healthcheck()
    assert health["configured"] is False, "ERROR: deberia ser False sin key"
    print("CASO 3 healthcheck configured=False:", "OK")

    # Caso 4: orchestrator importa sin claude_client directo
    import inspect
    from app.ai import orchestrator as orch_module
    source = inspect.getsource(orch_module)
    assert "from app.integrations.claude_client import ask" not in source, "ERROR: sigue usando claude_client directo"
    assert "provider_registry" in source, "ERROR: provider_registry no encontrado"
    print("CASO 4 orchestrator usa registry:", "OK")

    # Caso 5: orchestrator.generate retorna error controlado sin API key
    from app.ai.orchestrator import orchestrator
    result = await orchestrator.generate("test")
    assert result["success"] is False, "ERROR: deberia fallar sin key"
    assert result["error"] in ("auth_failed", "provider_error", "timeout"), f"ERROR: error_type inesperado={result['error']}"
    print("CASO 5 orchestrator sin key error controlado:", result["error"])

    print("--- TODOS LOS CASOS OK ---")

asyncio.run(main())