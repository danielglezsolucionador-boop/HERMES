import asyncio
from app.ai.provider_registry import provider_registry, setup_registry
from app.ai.orchestrator import orchestrator

async def main():
    setup_registry()
    print("Provider activo:", provider_registry.active_name())

    print("Ejecutando pipeline completo...")
    result = await orchestrator.generate("dame un resumen operacional breve del sistema")

    print("success:", result["success"])
    print("provider:", result["provider"])
    print("duration_ms:", result["duration_ms"])
    print("context_chars:", result["context_chars"])
    print("tokens_estimated:", result["tokens_estimated"])
    if result["success"]:
        print("response:", result["response"][:300])
    else:
        print("error:", result["error"])

asyncio.run(main())