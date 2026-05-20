"""
Temporary AI infrastructure validation endpoint.
This endpoint does not execute actions or validate real providers.
"""
import logging
import json

from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.orchestrator import orchestrator
from app.ai.context_builder import build_context
from app.ai.context_isolation import build_operational_context, sanitize_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


class AITestRequest(BaseModel):
    prompt: str = "Resume el estado operacional de Hermes."
    max_tokens: int = 128


def _build_ai_test_prompt(context: dict, user_prompt: str) -> str:
    isolated_context = build_operational_context(
        tasks=context.get("tasks", []),
        incidents=context.get("incidents", []),
        summary=context.get("summary", ""),
        runtime=context.get("runtime", {}),
        metadata=context.get("metadata", {}),
    )
    return "\n".join(
        [
            "HERMES OPERATIONAL CONTEXT",
            json.dumps(isolated_context, ensure_ascii=False, default=str),
            "",
            "USER REQUEST",
            sanitize_text(user_prompt, max_chars=2000),
        ]
    )


async def _run_ai_test(request: AITestRequest) -> dict:
    logger.info("ai_test: prompt_chars=%s", len(request.prompt))
    max_tokens = max(16, min(request.max_tokens, 512))
    return await orchestrator.generate(request.prompt, max_tokens=max_tokens)


@router.post("/test")
async def ai_test(request: AITestRequest) -> dict:
    return await _run_ai_test(request)


@router.get("/test")
async def ai_test_get() -> dict:
    return await _run_ai_test(AITestRequest())
