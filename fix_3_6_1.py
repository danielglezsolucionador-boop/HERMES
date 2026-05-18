import os

# ── 1. config.py — agregar CLAUDE_API_KEY ──────────────────────────────────
with open('app/core/config.py', 'r', encoding='utf-8') as f:
    src = f.read()

old = '    # Logging'
new = '    # Claude AI\n    CLAUDE_API_KEY: str = ""\n\n    # Logging'

if old in src and 'CLAUDE_API_KEY' not in src:
    src = src.replace(old, new, 1)
    with open('app/core/config.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('OK config.py — CLAUDE_API_KEY agregado')
else:
    print('SKIP config.py — ya existe o patron no encontrado')

# ── 2. Crear app/integrations/ ─────────────────────────────────────────────
os.makedirs('app/integrations', exist_ok=True)
with open('app/integrations/__init__.py', 'w', encoding='utf-8') as f:
    f.write('')
print('OK app/integrations/__init__.py creado')

# ── 3. Crear app/integrations/claude_client.py ────────────────────────────
claude_client = '''"""
claude_client.py — Subfase 3.6.1
Wrapper seguro para Claude API.
Desacoplado del runner, del Telegram y de las tasks.
Ref: docs/runtime_architecture.md
"""
import asyncio
import logging
import time
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-opus-4-20250514"
CLAUDE_TIMEOUT = 30  # segundos — timeout explícito obligatorio


def _is_configured() -> bool:
    """Valida que CLAUDE_API_KEY esté presente."""
    return bool(settings.CLAUDE_API_KEY and settings.CLAUDE_API_KEY.strip())


def validate_startup() -> None:
    """
    Llamar en startup.
    Warning si falta key — NO crashea el proceso.
    """
    if _is_configured():
        logger.info("claude_client: API key configurada — integración disponible")
    else:
        logger.warning("claude_client: CLAUDE_API_KEY no configurada — integración IA deshabilitada")


async def ask(prompt: str, max_tokens: int = 1024) -> dict:
    """
    Envía prompt a Claude. Retorna respuesta normalizada.

    Retorna:
    {
        "success": bool,
        "content": str,
        "model": str,
        "usage": {"input_tokens": int, "output_tokens": int},
        "duration_ms": int,
        "error": str | None,
        "error_type": str | None,
    }
    """
    if not _is_configured():
        logger.warning("claude_client: request bloqueada — API key no configurada")
        return _error_response("auth_failed", "CLAUDE_API_KEY no configurada", 0)

    headers = {
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    start_ms = time.monotonic()
    logger.info("claude_client: request iniciada model=%s max_tokens=%d", CLAUDE_MODEL, max_tokens)

    try:
        async with httpx.AsyncClient(timeout=CLAUDE_TIMEOUT) as client:
            response = await client.post(CLAUDE_API_URL, headers=headers, json=body)

        duration_ms = int((time.monotonic() - start_ms) * 1000)

        if response.status_code == 401:
            logger.error("claude_client: auth_failed status=401 duration_ms=%d", duration_ms)
            return _error_response("auth_failed", "API key inválida o sin permisos", duration_ms)

        if response.status_code == 429:
            logger.warning("claude_client: rate_limited status=429 duration_ms=%d", duration_ms)
            return _error_response("rate_limited", "Rate limit alcanzado", duration_ms)

        if response.status_code != 200:
            logger.error("claude_client: provider_error status=%d duration_ms=%d", response.status_code, duration_ms)
            return _error_response("provider_error", f"HTTP {response.status_code}", duration_ms)

        data = response.json()
        content_blocks = data.get("content", [])
        if not content_blocks or content_blocks[0].get("type") != "text":
            logger.error("claude_client: invalid_response — sin content text duration_ms=%d", duration_ms)
            return _error_response("invalid_response", "Respuesta sin content text", duration_ms)

        content = content_blocks[0]["text"]
        usage = data.get("usage", {})
        model = data.get("model", CLAUDE_MODEL)

        logger.info(
            "claude_client: request completada model=%s input_tokens=%d output_tokens=%d duration_ms=%d",
            model,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            duration_ms,
        )

        return {
            "success": True,
            "content": content,
            "model": model,
            "usage": {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            "duration_ms": duration_ms,
            "error": None,
            "error_type": None,
        }

    except asyncio.TimeoutError:
        duration_ms = int((time.monotonic() - start_ms) * 1000)
        logger.error("claude_client: timeout despues de %ds duration_ms=%d", CLAUDE_TIMEOUT, duration_ms)
        return _error_response("timeout", f"Timeout despues de {CLAUDE_TIMEOUT}s", duration_ms)

    except httpx.ConnectError as exc:
        duration_ms = int((time.monotonic() - start_ms) * 1000)
        logger.error("claude_client: provider_error connect_error=%s duration_ms=%d", exc, duration_ms)
        return _error_response("provider_error", "No se pudo conectar al proveedor", duration_ms)

    except Exception as exc:
        duration_ms = int((time.monotonic() - start_ms) * 1000)
        logger.error("claude_client: error inesperado=%s duration_ms=%d", exc, duration_ms)
        return _error_response("provider_error", str(exc), duration_ms)


def _error_response(error_type: str, error: str, duration_ms: int) -> dict:
    return {
        "success": False,
        "content": "",
        "model": CLAUDE_MODEL,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "duration_ms": duration_ms,
        "error": error,
        "error_type": error_type,
    }
'''

with open('app/integrations/claude_client.py', 'w', encoding='utf-8') as f:
    f.write(claude_client)
print('OK app/integrations/claude_client.py creado')

# ── 4. Crear app/api/ai.py ─────────────────────────────────────────────────
ai_router = '''"""
ai.py — Subfase 3.6.1
Endpoint temporal de validacion de integracion Claude.
NO conectado a tasks, Telegram, runner ni DB.
Solo validacion aislada.
"""
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from app.integrations.claude_client import ask

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


class AITestRequest(BaseModel):
    prompt: str


@router.post("/test")
async def ai_test(request: AITestRequest) -> dict:
    """
    Endpoint temporal de validacion Claude.
    Input:  {"prompt": "..."}
    Output: respuesta normalizada del claude_client.
    NO conectado a runtime, tasks ni Telegram.
    """
    logger.info("ai_test: request recibida prompt_len=%d", len(request.prompt))
    result = await ask(request.prompt)
    logger.info(
        "ai_test: completada success=%s duration_ms=%d",
        result["success"],
        result["duration_ms"],
    )
    return result
'''

with open('app/api/ai.py', 'w', encoding='utf-8') as f:
    f.write(ai_router)
print('OK app/api/ai.py creado')

# ── 5. Registrar router en __init__.py ─────────────────────────────────────
with open('app/api/__init__.py', 'r', encoding='utf-8') as f:
    src = f.read()

old = 'from app.api.runtime import router as runtime_router'
new = 'from app.api.runtime import router as runtime_router\nfrom app.api.ai import router as ai_router'

old2 = 'api_router.include_router(runtime_router)'
new2 = 'api_router.include_router(runtime_router)\napi_router.include_router(ai_router)'

if 'ai_router' not in src:
    src = src.replace(old, new, 1)
    src = src.replace(old2, new2, 1)
    with open('app/api/__init__.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('OK __init__.py — ai_router registrado')
else:
    print('SKIP __init__.py — ai_router ya existe')

print('fix_3_6_1.py completado')