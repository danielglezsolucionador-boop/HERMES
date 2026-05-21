"""
Simple task executor for Hermes runner.
Architecture: Task -> Runner -> Executor -> PostgreSQL.
"""
import asyncio
import logging
import time

from app.models.task import Task

logger = logging.getLogger(__name__)

EXECUTOR_TIMEOUT = 30
AI_EXECUTOR_VALUES = {"ai", "provider", "llm"}
AI_PROVIDER_HINTS = {
    "ai",
    "claude",
    "deepseek",
    "gemini",
    "llm",
    "openai",
    "openrouter",
    "vulcan",
    "vulcano",
}
AI_MODEL_PREFIXES = (
    "anthropic/",
    "claude",
    "deepseek/",
    "gemini",
    "gpt-",
    "llama",
    "mistral",
    "openai/",
    "qwen",
)


def _normalized_payload_value(payload: dict, key: str) -> str:
    value = payload.get(key)
    return str(value or "").strip().lower()


def is_ai_task_payload(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False

    executor = _normalized_payload_value(payload, "executor")
    task_type = _normalized_payload_value(payload, "type")
    agent = _normalized_payload_value(payload, "agent")
    provider = _normalized_payload_value(payload, "provider")
    model = _normalized_payload_value(payload, "model")

    return (
        executor in AI_EXECUTOR_VALUES
        or task_type in AI_EXECUTOR_VALUES
        or agent in AI_PROVIDER_HINTS
        or provider in AI_PROVIDER_HINTS
        or any(model.startswith(prefix) for prefix in AI_MODEL_PREFIXES)
    )


async def _run(task: Task) -> dict:
    start = time.monotonic()

    simulate = None
    payload = task.payload if isinstance(task.payload, dict) else {}
    if isinstance(task.payload, dict):
        simulate = task.payload.get("simulate")

    if simulate == "fail":
        logger.warning("executor: simulated failure task_id=%s", task.id)
        raise ValueError("Simulated failure via payload.simulate=fail")

    if simulate == "timeout":
        logger.warning("executor: simulated timeout task_id=%s", task.id)
        await asyncio.sleep(EXECUTOR_TIMEOUT + 5)

    if is_ai_task_payload(payload):
        return await _run_ai_task(task, payload, start)

    await asyncio.sleep(1)
    duration_ms = int((time.monotonic() - start) * 1000)

    return {
        "executed": True,
        "task_id": str(task.id),
        "executor": "default",
        "duration_ms": duration_ms,
        "message": "Task ejecutada correctamente",
    }


async def _run_ai_task(task: Task, payload: dict, start: float) -> dict:
    from app.ai.orchestrator import orchestrator

    prompt = payload.get("prompt") or task.description or task.title
    max_tokens = int(payload.get("max_tokens") or 1024)
    logger.info("executor: ai task starting task_id=%s prompt_chars=%s", task.id, len(prompt))

    ai_result = await orchestrator.generate(prompt, max_tokens=max_tokens)
    duration_ms = int((time.monotonic() - start) * 1000)
    if not ai_result.get("success"):
        detail = ai_result.get("error_detail") or ai_result.get("error") or "AI provider unavailable"
        raise RuntimeError(f"AI task failed: {detail}")

    return {
        "executed": True,
        "task_id": str(task.id),
        "executor": "ai",
        "duration_ms": duration_ms,
        "provider": ai_result.get("provider"),
        "model": ai_result.get("model"),
        "response": ai_result.get("response"),
        "handoff": ai_result.get("handoff"),
        "usage": ai_result.get("usage"),
        "message": "AI task ejecutada correctamente",
    }


async def execute_task(task: Task) -> dict:
    """Execute one task with a controlled timeout."""
    logger.info("executor: starting task_id=%s title=%s", task.id, task.title)
    try:
        result = await asyncio.wait_for(_run(task), timeout=EXECUTOR_TIMEOUT)
    except asyncio.TimeoutError as exc:
        logger.error("executor: timeout task_id=%s timeout=%s", task.id, EXECUTOR_TIMEOUT)
        raise RuntimeError(f"Executor timeout after {EXECUTOR_TIMEOUT}s") from exc

    logger.info(
        "executor: completed task_id=%s duration_ms=%s",
        task.id,
        result.get("duration_ms"),
    )
    return result
