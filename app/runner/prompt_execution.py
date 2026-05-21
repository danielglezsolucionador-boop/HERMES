"""
Controlled prompt execution for Hermes provider runtime.

This layer builds validated operational prompts and sends them through the
existing ProviderBridge. It does not route providers, retry prompts, mutate
tasks, approve responses, or run autonomous work.
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.runner.provider_bridge import (
    ProviderBridge,
    ProviderBridgeRequest,
    ProviderBridgeResult,
)
from app.runner.task_execution import (
    EXECUTION_STATE_EXECUTING,
    ExecutionContext,
)

logger = logging.getLogger(__name__)

PROMPT_TYPE_EXECUTION = "execution"
PROMPT_TYPE_VALIDATION = "validation"
PROMPT_TYPE_AUDIT = "audit"
PROMPT_TYPE_REPORTING = "reporting"
SUPPORTED_PROMPT_TYPES = {
    PROMPT_TYPE_EXECUTION,
    PROMPT_TYPE_VALIDATION,
    PROMPT_TYPE_AUDIT,
    PROMPT_TYPE_REPORTING,
}

PROMPT_STATE_BUILDING = "building"
PROMPT_STATE_READY = "ready"
PROMPT_STATE_SENDING = "sending"
PROMPT_STATE_WAITING_RESPONSE = "waiting_response"
PROMPT_STATE_COMPLETED = "completed"
PROMPT_STATE_FAILED = "failed"
PROMPT_STATE_REJECTED = "rejected"


@dataclass(frozen=True)
class PromptExecutionRequest:
    execution: ExecutionContext
    objective: str
    prompt_type: str = PROMPT_TYPE_EXECUTION
    context_data: dict[str, Any] = field(default_factory=dict)
    execution_limits: tuple[str, ...] = field(default_factory=tuple)
    expected_output: str = ""
    validation_rules: tuple[str, ...] = field(default_factory=tuple)
    audit_requirements: tuple[str, ...] = field(default_factory=tuple)
    provider_name: str | None = None
    system_prompt: str | None = None
    max_tokens: int = 1024
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PromptExecutionResult:
    status: str
    success: bool
    prompt_execution_id: str
    prompt_type: str
    prompt_status: str
    objective: str | None = None
    provider_name: str | None = None
    provider_session_id: str | None = None
    request_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    prompt_size_bytes: int = 0
    output: str | None = None
    output_size_bytes: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    provider_duration_ms: int = 0
    usage: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    lifecycle: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    provider_result: ProviderBridgeResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "prompt_execution_id": self.prompt_execution_id,
            "prompt_type": self.prompt_type,
            "prompt_status": self.prompt_status,
            "objective": self.objective,
            "provider_name": self.provider_name,
            "provider_session_id": self.provider_session_id,
            "request_id": self.request_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "prompt_size_bytes": self.prompt_size_bytes,
            "output_available": bool(self.output),
            "output_size_bytes": self.output_size_bytes,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "provider_duration_ms": self.provider_duration_ms,
            "usage": dict(self.usage),
            "reasons": list(self.reasons),
            "error": self.error,
            "lifecycle": [dict(entry) for entry in self.lifecycle],
            "provider_result": (
                self.provider_result.to_dict() if self.provider_result else None
            ),
        }


class PromptExecutionRuntime:
    def __init__(
        self,
        provider_bridge: ProviderBridge | None = None,
        status: Any | None = None,
        max_prompt_bytes: int | None = None,
    ) -> None:
        self.provider_bridge = provider_bridge or ProviderBridge()
        self.status = status
        bridge_visibility = self.provider_bridge.visibility()
        self.max_prompt_bytes = max(
            1,
            int(max_prompt_bytes or bridge_visibility["max_request_bytes"]),
        )

    async def execute(
        self,
        request: PromptExecutionRequest,
        runtime_active: bool = True,
        execution_permitted: bool = True,
    ) -> PromptExecutionResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        prompt_execution_id = str(uuid4())
        lifecycle = (
            self._lifecycle(PROMPT_STATE_BUILDING),
        )

        try:
            reasons = self._validation_reasons(
                request,
                runtime_active,
                execution_permitted,
            )
            if reasons:
                result = self._result(
                    status="rejected",
                    success=False,
                    prompt_execution_id=prompt_execution_id,
                    prompt_type=request.prompt_type,
                    prompt_status=PROMPT_STATE_REJECTED,
                    objective=request.objective,
                    request=request,
                    reasons=reasons,
                    lifecycle=(
                        *lifecycle,
                        self._lifecycle(PROMPT_STATE_REJECTED),
                    ),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            prompt = self._build_prompt(request)
            if len(prompt.encode("utf-8")) > self.max_prompt_bytes:
                result = self._result(
                    status="rejected",
                    success=False,
                    prompt_execution_id=prompt_execution_id,
                    prompt_type=request.prompt_type,
                    prompt_status=PROMPT_STATE_REJECTED,
                    objective=request.objective,
                    request=request,
                    prompt=prompt,
                    reasons=["max_prompt_size_exceeded"],
                    lifecycle=(
                        *lifecycle,
                        self._lifecycle(PROMPT_STATE_READY),
                        self._lifecycle(PROMPT_STATE_REJECTED),
                    ),
                    started=started,
                    started_at=started_at,
                )
                self._publish(result)
                self._log_result(result)
                return result

            lifecycle = (
                *lifecycle,
                self._lifecycle(PROMPT_STATE_READY),
                self._lifecycle(PROMPT_STATE_SENDING),
                self._lifecycle(PROMPT_STATE_WAITING_RESPONSE),
            )
            provider_result = await self.provider_bridge.send(
                ProviderBridgeRequest(
                    execution=request.execution,
                    prompt=prompt,
                    system_prompt=request.system_prompt or self._system_prompt(),
                    provider_name=request.provider_name,
                    max_tokens=request.max_tokens,
                    metadata={
                        "prompt_execution_id": prompt_execution_id,
                        "prompt_type": request.prompt_type,
                        **dict(request.metadata),
                    },
                ),
                runtime_active=runtime_active,
            )
            if provider_result.success:
                prompt_status = PROMPT_STATE_COMPLETED
                status = "completed"
                success = True
                reasons: Sequence[str] = ()
                error = None
            else:
                prompt_status = PROMPT_STATE_FAILED
                status = provider_result.status or "provider_failed"
                success = False
                reasons = provider_result.reasons
                error = provider_result.error

            result = self._result(
                status=status,
                success=success,
                prompt_execution_id=prompt_execution_id,
                prompt_type=request.prompt_type,
                prompt_status=prompt_status,
                objective=request.objective,
                request=request,
                prompt=prompt,
                output=provider_result.content,
                provider_result=provider_result,
                reasons=list(reasons),
                error=error,
                lifecycle=(
                    *lifecycle,
                    self._lifecycle(prompt_status),
                ),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                status="error",
                success=False,
                prompt_execution_id=prompt_execution_id,
                prompt_type=request.prompt_type,
                prompt_status=PROMPT_STATE_FAILED,
                objective=request.objective,
                request=request,
                reasons=["prompt_execution_error_contained"],
                error=str(exc),
                lifecycle=(
                    *lifecycle,
                    self._lifecycle(PROMPT_STATE_FAILED),
                ),
                started=started,
                started_at=started_at,
            )
            self._publish(result)
            self._log_result(result)
            return result

    def _validation_reasons(
        self,
        request: PromptExecutionRequest,
        runtime_active: bool,
        execution_permitted: bool,
    ) -> list[str]:
        reasons: list[str] = []
        if not runtime_active:
            reasons.append("runtime_inactive")
        if not execution_permitted:
            reasons.append("prompt_execution_not_permitted")
        if request.prompt_type not in SUPPORTED_PROMPT_TYPES:
            reasons.append("unsupported_prompt_type")
        if request.execution.execution_state != EXECUTION_STATE_EXECUTING:
            reasons.append("execution_not_active")
        if not request.execution.execution_id:
            reasons.append("missing_execution_id")
        if not request.execution.task_id:
            reasons.append("missing_task_id")
        if not request.objective or not request.objective.strip():
            reasons.append("missing_execution_objective")
        if not isinstance(request.context_data, dict) or not request.context_data:
            reasons.append("missing_context_data")
        if not self._has_items(request.execution_limits):
            reasons.append("missing_execution_limits")
        if not request.expected_output or not request.expected_output.strip():
            reasons.append("missing_expected_output")
        if not self._has_items(request.validation_rules):
            reasons.append("missing_validation_rules")
        if not self._has_items(request.audit_requirements):
            reasons.append("missing_audit_requirements")
        if request.max_tokens < 1:
            reasons.append("invalid_max_tokens")
        if self._has_control_characters(request.objective):
            reasons.append("malformed_prompt_objective")
        if self._has_control_characters(request.expected_output):
            reasons.append("malformed_expected_output")
        return reasons

    def _build_prompt(self, request: PromptExecutionRequest) -> str:
        context_json = json.dumps(
            request.context_data,
            ensure_ascii=True,
            sort_keys=True,
            default=str,
        )
        metadata_json = json.dumps(
            request.metadata,
            ensure_ascii=True,
            sort_keys=True,
            default=str,
        )
        sections = [
            ("PROMPT TYPE", request.prompt_type),
            ("EXECUTION OBJECTIVE", request.objective.strip()),
            ("EXECUTION CONTEXT", self._execution_context_text(request.execution)),
            ("CONTEXT DATA", context_json),
            ("EXECUTION LIMITS", self._bullet_list(request.execution_limits)),
            ("EXPECTED OUTPUT", request.expected_output.strip()),
            ("VALIDATION RULES", self._bullet_list(request.validation_rules)),
            ("AUDIT REQUIREMENTS", self._bullet_list(request.audit_requirements)),
            ("METADATA", metadata_json),
        ]
        return "\n\n".join(f"{title}\n{body}" for title, body in sections)

    def _execution_context_text(self, execution: ExecutionContext) -> str:
        return "\n".join(
            [
                f"execution_id: {execution.execution_id}",
                f"task_id: {execution.task_id}",
                f"runner_id: {execution.runner_id}",
                f"runtime_id: {execution.runtime_id}",
                f"runtime_owner: {execution.runtime_owner}",
                f"execution_state: {execution.execution_state}",
            ]
        )

    def _bullet_list(self, values: Sequence[str]) -> str:
        return "\n".join(f"- {str(value).strip()}" for value in values)

    def _system_prompt(self) -> str:
        return (
            "You are Hermes operational execution. Follow the provided limits, "
            "preserve runtime context, and return only the expected output."
        )

    def _has_items(self, values: Sequence[str]) -> bool:
        return any(str(value).strip() for value in values)

    def _has_control_characters(self, value: str) -> bool:
        return any(ord(char) < 32 and char not in {"\n", "\r", "\t"} for char in value)

    def _lifecycle(self, state: str) -> dict[str, Any]:
        return {
            "state": state,
            "at": datetime.now(timezone.utc).isoformat(),
        }

    def _result(
        self,
        status: str,
        success: bool,
        prompt_execution_id: str,
        prompt_type: str,
        prompt_status: str,
        objective: str | None = None,
        request: PromptExecutionRequest | None = None,
        prompt: str | None = None,
        output: str | None = None,
        provider_result: ProviderBridgeResult | None = None,
        reasons: list[str] | None = None,
        error: str | None = None,
        lifecycle: tuple[dict[str, Any], ...] = (),
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> PromptExecutionResult:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        prompt_bytes = len(prompt.encode("utf-8")) if prompt else 0
        output_bytes = len(output.encode("utf-8")) if output else 0
        execution = request.execution if request else None
        return PromptExecutionResult(
            status=status,
            success=success,
            prompt_execution_id=prompt_execution_id,
            prompt_type=prompt_type,
            prompt_status=prompt_status,
            objective=objective,
            provider_name=(
                provider_result.provider_name
                if provider_result
                else (request.provider_name if request else None)
            ),
            provider_session_id=(
                provider_result.provider_session_id if provider_result else None
            ),
            request_id=provider_result.request_id if provider_result else None,
            execution_id=execution.execution_id if execution else None,
            task_id=execution.task_id if execution else None,
            prompt_size_bytes=prompt_bytes,
            output=output,
            output_size_bytes=output_bytes,
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            provider_duration_ms=(
                provider_result.provider_duration_ms if provider_result else 0
            ),
            usage=provider_result.usage if provider_result else {},
            reasons=tuple(reasons or []),
            error=error,
            lifecycle=lifecycle,
            provider_result=provider_result,
        )

    def _publish(self, result: PromptExecutionResult) -> None:
        if self.status is not None and hasattr(
            self.status,
            "mark_prompt_execution_result",
        ):
            self.status.mark_prompt_execution_result(result.to_dict())

    def _log_result(self, result: PromptExecutionResult) -> None:
        if result.success:
            logger.info(
                "prompt_execution: completed prompt_execution_id=%s provider=%s duration_ms=%s",
                result.prompt_execution_id,
                result.provider_name,
                result.duration_ms,
            )
            return
        if result.status == "rejected":
            logger.warning(
                "prompt_execution: rejected prompt_execution_id=%s reasons=%s",
                result.prompt_execution_id,
                ",".join(result.reasons),
            )
            return
        logger.error(
            "prompt_execution: failed prompt_execution_id=%s status=%s reasons=%s error=%s",
            result.prompt_execution_id,
            result.status,
            ",".join(result.reasons),
            result.error,
        )
