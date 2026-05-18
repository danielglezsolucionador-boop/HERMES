import asyncio
from app.ai.provider_registry import provider_registry, setup_registry

async def main():
    setup_registry()
    provider = provider_registry.get_active()

    print("Enviando request REAL a OpenRouter...")
    result = await provider.generate(
        prompt="Responde en una sola frase: cual es el estado operacional de un sistema sin errores.",
        system_prompt="Eres un componente interno de Hermes. Responde de forma breve y operacional.",
        max_tokens=100,
    )

    print("success:", result["success"])
    print("model:", result["model"])
    print("duration_ms:", result["duration_ms"])
    print("input_tokens:", result["usage"]["input_tokens"])
    print("output_tokens:", result["usage"]["output_tokens"])
    if result["success"]:
        print("content:", result["content"][:200])
    else:
        print("error:", result["error"])
        print("error_type:", result["error_type"])

asyncio.run(main())