"""
Controlled provider bridge for Hermes execution runtime.

This layer sends validated requests to AI providers and normalizes responses.
It does not claim tasks, execute tasks autonomously, retry requests, orchestrate
multiple providers, or mutate runtime state outside its own in-memory counters.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.ai.provider_registry import provider_registry, setup_registry
from app.ai.providers.base import AIProvider
from app.core.config import settings
from app.runner.task_execution import (
    EXECUTION_STATE_EXECUTING,
    ExecutionContext,
)

logger = logging.getLogger(__name__)

ProviderResolver = Callable[[str | None], AIProvider]

PROVIDER_CONNECTION_CONNECTING = "connecting"
PROVIDER_CONNECTION_CONNECTED = "connected"
PROVIDER_CONNECTION_EXECUTING = "executing"
PROVIDER_CONNECTION_WAITING_RESPONSE = "waiting_response"
PROVIDER_CONNECTION_FAILED = "failed"
PROVIDER_CONNECTION_CLOSED = "closed"

PROVIDER_CONNECTION_TERMINAL_STATES = {
    PROVIDER_CONNECTION_FAILED,
    PROVIDER_CONNECTION_CLOSED,
}


@dataclass(frozen=True)
class ProviderBridgeRequest:
    execution: ExecutionContext
    prompt: str
    system_prompt: str | None = None
    provider_name: str | None = None
    max_tokens: int = 1024
    metadata: dict[str, Any] = field(default_factory=dict)

    def request_size_bytes(self) -> int:
        body = (self.system_prompt or "") + self.prompt
        return len(body.encode("utf-8"))


@dataclass(frozen=True)
class ProviderBridgeContext:
    request_id: str
    execution_id: str
    task_id: str
    runner_id: str
    runtime_id: str
    runtime_owner: str
    provider_name: str
    built_at: str
    request_size_bytes: int
    timeout_seconds: float
    max_tokens: int
    provider_session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "provider_session_id": self.provider_session_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runner_id": self.runner_id,
            "runtime_id": self.runtime_id,
            "runtime_owner": self.runtime_owner,
            "provider_name": self.provider_name,
            "built_at": self.built_at,
            "request_size_bytes": self.request_size_bytes,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
        }


@dataclass(frozen=True)
class ProviderConnectionSession:
    provider_session_id: str
    provider_id: str
    request_id: str
    execution_id: str
    task_id: str
    runner_id: str
    runtime_id: str
    runtime_owner: str
    execution_context: dict[str, Any]
    connection_status: str = PROVIDER_CONNECTION_CONNECTING
    failure_status: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    closed_at: str | None = None
    state_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_session_id": self.provider_session_id,
            "provider_id": self.provider_id,
            "request_id": self.request_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "runner_id": self.runner_id,
            "runtime_id": self.runtime_id,
            "runtime_owner": self.runtime_owner,
            "execution_context": dict(self.execution_context),
            "connection_status": self.connection_status,
            "failure_status": self.failure_status,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
            "state_history": [dict(entry) for entry in self.state_history],
        }


@dataclass(frozen=True)
class ProviderBridgeResult:
    status: str
    success: bool
    provider_name: str | None = None
    provider_session_id: str | None = None
    connection_status: str | None = None
    failure_status: str | None = None
    connection_states: tuple[str, ...] = field(default_factory=tuple)
    model: str | None = None
    content: str | None = None
    request_id: str | None = None
    execution_id: str | None = None
    task_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int = 0
    provider_duration_ms: int = 0
    usage: dict[str, Any] = field(default_factory=dict)
    active_provider_calls: int = 0
    max_concurrent_provider_calls: int = 0
    max_requests_per_minute: int = 0
    requests_in_window: int = 0
    active_provider_sessions: int = 0
    max_request_bytes: int = 0
    request_size_bytes: int = 0
    timeout_seconds: float = 0.0
    max_response_bytes: int = 0
    response_size_bytes: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    context: ProviderBridgeContext | None = None
    connection: ProviderConnectionSession | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "provider_name": self.provider_name,
            "provider_session_id": self.provider_session_id,
            "connection_status": self.connection_status,
            "failure_status": self.failure_status,
            "connection_states": list(self.connection_states),
            "model": self.model,
            "request_id": self.request_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "provider_duration_ms": self.provider_duration_ms,
            "usage": dict(self.usage),
            "active_provider_calls": self.active_provider_calls,
            "max_concurrent_provider_calls": self.max_concurrent_provider_calls,
            "max_requests_per_minute": self.max_requests_per_minute,
            "requests_in_window": self.requests_in_window,
            "active_provider_sessions": self.active_provider_sessions,
            "max_request_bytes": self.max_request_bytes,
            "request_size_bytes": self.request_size_bytes,
            "timeout_seconds": self.timeout_seconds,
            "max_response_bytes": self.max_response_bytes,
            "response_size_bytes": self.response_size_bytes,
            "reasons": list(self.reasons),
            "error": self.error,
            "context": self.context.to_dict() if self.context else None,
            "connection": self.connection.to_dict() if self.connection else None,
        }


class ProviderBridge:
    def __init__(
        self,
        max_requests_per_minute: int = settings.PROVIDER_BRIDGE_MAX_REQUESTS_PER_MINUTE,
        max_request_bytes: int = settings.PROVIDER_BRIDGE_MAX_REQUEST_BYTES,
        timeout_seconds: float = settings.PROVIDER_BRIDGE_TIMEOUT_SECONDS,
        max_concurrent_calls: int = settings.PROVIDER_BRIDGE_MAX_CONCURRENT_CALLS,
        max_response_bytes: int = settings.PROVIDER_BRIDGE_MAX_RESPONSE_BYTES,
        max_tokens: int = settings.PROVIDER_BRIDGE_MAX_TOKENS,
        provider_resolver: ProviderResolver | None = None,
    ) -> None:
        self.max_requests_per_minute = max(1, int(max_requests_per_minute or 1))
        self.max_request_bytes = max(1, int(max_request_bytes or 1))
        self.timeout_seconds = max(0.1, float(timeout_seconds or 0.1))
        self.max_concurrent_calls = max(1, int(max_concurrent_calls or 1))
        self.max_response_bytes = max(1, int(max_response_bytes or 1))
        self.max_tokens = max(1, int(max_tokens or 1))
        self.provider_resolver = provider_resolver or self._resolve_provider
        self._active_calls = 0
        self._request_window: list[datetime] = []
        self._active_connections: dict[str, ProviderConnectionSession] = {}
        self._last_connection: ProviderConnectionSession | None = None

    async def send(
        self,
        request: ProviderBridgeRequest,
        runtime_active: bool = True,
    ) -> ProviderBridgeResult:
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        provider: AIProvider | None = None
        context: ProviderBridgeContext | None = None
        connection: ProviderConnectionSession | None = None

        try:
            reasons = self._request_reasons(request, runtime_active)
            if reasons:
                result = self._result(
                    "rejected",
                    False,
                    request=request,
                    reasons=reasons,
                    started=started,
                    started_at=started_at,
                )
                self._log_result(result)
                return result

            try:
                provider = self.provider_resolver(request.provider_name)
            except Exception as exc:
                result = self._result(
                    "rejected",
                    False,
                    request=request,
                    provider_name=request.provider_name,
                    reasons=["provider_not_configured", "provider_unavailable"],
                    error=str(exc),
                    started=started,
                    started_at=started_at,
                )
                self._log_result(result)
                return result

            provider_name = provider.provider_name
            context = self._build_context(request, provider_name)
            context, connection = self._open_connection(context)
            health = await self._safe_healthcheck(provider)
            health_reasons = self._health_reasons(health)
            if health_reasons:
                connection = self._fail_connection(
                    connection,
                    health_reasons,
                    health.get("last_error"),
                )
                result = self._result(
                    "rejected",
                    False,
                    context=context,
                    request=request,
                    connection=connection,
                    reasons=health_reasons,
                    error=health.get("last_error"),
                    started=started,
                    started_at=started_at,
                )
                self._log_result(result)
                return result

            connection = self._transition_connection(
                connection,
                PROVIDER_CONNECTION_CONNECTED,
            )
            connection = self._transition_connection(
                connection,
                PROVIDER_CONNECTION_EXECUTING,
            )
            self._record_request_window()
            self._active_calls += 1
            try:
                connection = self._transition_connection(
                    connection,
                    PROVIDER_CONNECTION_WAITING_RESPONSE,
                )
                response = await asyncio.wait_for(
                    provider.generate(
                        request.prompt,
                        system_prompt=request.system_prompt,
                        max_tokens=min(max(1, request.max_tokens), self.max_tokens),
                    ),
                    timeout=self.timeout_seconds,
                )
            finally:
                self._active_calls = max(0, self._active_calls - 1)

            result = self._ingest_response(
                response=response,
                context=context,
                connection=connection,
                request=request,
                started=started,
                started_at=started_at,
            )
            self._log_result(result)
            return result
        except asyncio.TimeoutError:
            result = self._result(
                "timeout",
                False,
                context=context,
                request=request,
                provider_name=provider.provider_name if provider else None,
                connection=(
                    self._fail_connection(
                        connection,
                        ["provider_timeout"],
                        f"Provider timeout after {self.timeout_seconds}s",
                    )
                    if connection
                    else None
                ),
                reasons=["provider_timeout"],
                error=f"Provider timeout after {self.timeout_seconds}s",
                started=started,
                started_at=started_at,
            )
            self._log_result(result)
            return result
        except Exception as exc:
            result = self._result(
                "error",
                False,
                context=context,
                request=request,
                provider_name=provider.provider_name if provider else None,
                connection=(
                    self._fail_connection(
                        connection,
                        ["provider_bridge_error_contained"],
                        str(exc),
                    )
                    if connection
                    else None
                ),
                reasons=["provider_bridge_error_contained"],
                error=str(exc),
                started=started,
                started_at=started_at,
            )
            self._log_result(result)
            return result

    def visibility(self) -> dict[str, Any]:
        self._trim_request_window()
        last_connection = self._last_connection
        return {
            "active_provider_calls": self._active_calls,
            "active_provider_sessions": len(self._active_connections),
            "max_concurrent_provider_calls": self.max_concurrent_calls,
            "max_requests_per_minute": self.max_requests_per_minute,
            "requests_in_window": len(self._request_window),
            "max_request_bytes": self.max_request_bytes,
            "timeout_seconds": self.timeout_seconds,
            "max_response_bytes": self.max_response_bytes,
            "max_tokens": self.max_tokens,
            "provider_session_id": (
                last_connection.provider_session_id if last_connection else None
            ),
            "connection_status": (
                last_connection.connection_status if last_connection else None
            ),
            "failure_status": (
                last_connection.failure_status if last_connection else None
            ),
            "connection_states": (
                self._connection_states(last_connection)
                if last_connection
                else []
            ),
            "connection": last_connection.to_dict() if last_connection else None,
        }

    def _resolve_provider(self, name: str | None) -> AIProvider:
        if provider_registry.active_name() is None:
            setup_registry()
        if name:
            provider = provider_registry.get(name)
            if provider is None:
                raise ValueError(f"Provider '{name}' not registered")
            return provider
        return provider_registry.get_active()

    def _request_reasons(
        self,
        request: ProviderBridgeRequest,
        runtime_active: bool,
    ) -> list[str]:
        self._trim_request_window()
        reasons: list[str] = []
        execution = request.execution
        if not runtime_active:
            reasons.append("runtime_inactive")
        if execution.execution_state != EXECUTION_STATE_EXECUTING:
            reasons.append("execution_not_active")
        if not execution.execution_id:
            reasons.append("missing_execution_id")
        if not execution.task_id:
            reasons.append("missing_task_id")
        if not request.prompt or not request.prompt.strip():
            reasons.append("empty_provider_prompt")
        if request.request_size_bytes() > self.max_request_bytes:
            reasons.append("max_request_size_exceeded")
        if request.max_tokens < 1:
            reasons.append("invalid_max_tokens")
        if self._active_calls >= self.max_concurrent_calls:
            reasons.append("max_concurrent_provider_calls_reached")
        if len(self._request_window) >= self.max_requests_per_minute:
            reasons.append("max_provider_requests_reached")
        return reasons

    async def _safe_healthcheck(self, provider: AIProvider) -> dict:
        try:
            result = await asyncio.wait_for(
                provider.healthcheck(),
                timeout=min(self.timeout_seconds, 5.0),
            )
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            return {
                "available": False,
                "configured": False,
                "last_error": str(exc),
            }

    def _health_reasons(self, health: dict) -> list[str]:
        reasons: list[str] = []
        if not health.get("configured"):
            reasons.append("provider_not_configured")
        if not health.get("available"):
            reasons.append("provider_unavailable")
        return reasons

    def _build_context(
        self,
        request: ProviderBridgeRequest,
        provider_name: str,
    ) -> ProviderBridgeContext:
        execution = request.execution
        return ProviderBridgeContext(
            request_id=str(uuid4()),
            execution_id=execution.execution_id,
            task_id=execution.task_id,
            runner_id=execution.runner_id,
            runtime_id=execution.runtime_id,
            runtime_owner=execution.runtime_owner,
            provider_name=provider_name,
            built_at=datetime.now(timezone.utc).isoformat(),
            request_size_bytes=request.request_size_bytes(),
            timeout_seconds=self.timeout_seconds,
            max_tokens=min(max(1, request.max_tokens), self.max_tokens),
        )

    def _ingest_response(
        self,
        response: dict,
        context: ProviderBridgeContext,
        connection: ProviderConnectionSession,
        request: ProviderBridgeRequest,
        started: float,
        started_at: datetime,
    ) -> ProviderBridgeResult:
        if not isinstance(response, dict):
            connection = self._fail_connection(
                connection,
                ["provider_response_not_mapping"],
                "Provider response was not a mapping",
            )
            return self._result(
                "invalid_response",
                False,
                context=context,
                connection=connection,
                request=request,
                reasons=["provider_response_not_mapping"],
                error="Provider response was not a mapping",
                started=started,
                started_at=started_at,
            )

        if not response.get("success"):
            reasons = [response.get("error_type") or "provider_error"]
            connection = self._fail_connection(
                connection,
                reasons,
                response.get("error") or "Provider request failed",
                usage=response.get("usage") or {},
            )
            return self._result(
                "provider_error",
                False,
                context=context,
                connection=connection,
                request=request,
                model=response.get("model"),
                usage=response.get("usage") or {},
                provider_duration_ms=int(response.get("duration_ms") or 0),
                reasons=reasons,
                error=response.get("error") or "Provider request failed",
                started=started,
                started_at=started_at,
            )

        content = response.get("content")
        if not isinstance(content, str) or not content.strip():
            connection = self._fail_connection(
                connection,
                ["empty_provider_response"],
                "Provider response content was empty",
                usage=response.get("usage") or {},
            )
            return self._result(
                "invalid_response",
                False,
                context=context,
                connection=connection,
                request=request,
                model=response.get("model"),
                usage=response.get("usage") or {},
                provider_duration_ms=int(response.get("duration_ms") or 0),
                reasons=["empty_provider_response"],
                error="Provider response content was empty",
                started=started,
                started_at=started_at,
            )

        response_size = len(content.encode("utf-8"))
        if response_size > self.max_response_bytes:
            connection = self._fail_connection(
                connection,
                ["max_response_size_exceeded"],
                "Provider response exceeded max size",
                usage=response.get("usage") or {},
            )
            return self._result(
                "invalid_response",
                False,
                context=context,
                connection=connection,
                request=request,
                model=response.get("model"),
                usage=response.get("usage") or {},
                provider_duration_ms=int(response.get("duration_ms") or 0),
                response_size_bytes=response_size,
                reasons=["max_response_size_exceeded"],
                error="Provider response exceeded max size",
                started=started,
                started_at=started_at,
            )

        if request.execution.execution_state != EXECUTION_STATE_EXECUTING:
            connection = self._fail_connection(
                connection,
                ["execution_no_longer_active"],
                "Execution context changed before response ingestion",
                usage=response.get("usage") or {},
            )
            return self._result(
                "invalid_response",
                False,
                context=context,
                connection=connection,
                request=request,
                model=response.get("model"),
                usage=response.get("usage") or {},
                provider_duration_ms=int(response.get("duration_ms") or 0),
                reasons=["execution_no_longer_active"],
                error="Execution context changed before response ingestion",
                started=started,
                started_at=started_at,
            )

        connection = self._close_connection(
            connection,
            usage=response.get("usage") or {},
        )
        return self._result(
            "completed",
            True,
            context=context,
            connection=connection,
            request=request,
            model=response.get("model"),
            content=content,
            usage=response.get("usage") or {},
            provider_duration_ms=int(response.get("duration_ms") or 0),
            response_size_bytes=response_size,
            started=started,
            started_at=started_at,
        )

    def _open_connection(
        self,
        context: ProviderBridgeContext,
    ) -> tuple[ProviderBridgeContext, ProviderConnectionSession]:
        provider_session_id = str(uuid4())
        connected_context = replace(
            context,
            provider_session_id=provider_session_id,
        )
        connection = ProviderConnectionSession(
            provider_session_id=provider_session_id,
            provider_id=context.provider_name,
            request_id=context.request_id,
            execution_id=context.execution_id,
            task_id=context.task_id,
            runner_id=context.runner_id,
            runtime_id=context.runtime_id,
            runtime_owner=context.runtime_owner,
            execution_context={
                "execution_id": context.execution_id,
                "task_id": context.task_id,
                "runner_id": context.runner_id,
                "runtime_id": context.runtime_id,
                "runtime_owner": context.runtime_owner,
            },
            state_history=(
                self._connection_state_event(PROVIDER_CONNECTION_CONNECTING),
            ),
        )
        return connected_context, self._store_connection(connection)

    def _transition_connection(
        self,
        connection: ProviderConnectionSession,
        state: str,
        failure_status: str | None = None,
        usage: dict[str, Any] | None = None,
    ) -> ProviderConnectionSession:
        now = datetime.now(timezone.utc).isoformat()
        input_tokens, output_tokens = self._token_usage(connection, usage)
        updated = replace(
            connection,
            connection_status=state,
            failure_status=failure_status or connection.failure_status,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            updated_at=now,
            closed_at=(
                now if state in PROVIDER_CONNECTION_TERMINAL_STATES else connection.closed_at
            ),
            state_history=(
                *connection.state_history,
                self._connection_state_event(state, failure_status),
            ),
        )
        return self._store_connection(updated)

    def _fail_connection(
        self,
        connection: ProviderConnectionSession,
        reasons: list[str],
        error: str | None = None,
        usage: dict[str, Any] | None = None,
    ) -> ProviderConnectionSession:
        failure_status = ",".join(str(reason) for reason in reasons if reason)
        if error and not failure_status:
            failure_status = error
        return self._transition_connection(
            connection,
            PROVIDER_CONNECTION_FAILED,
            failure_status=failure_status or "provider_connection_failed",
            usage=usage,
        )

    def _close_connection(
        self,
        connection: ProviderConnectionSession,
        usage: dict[str, Any] | None = None,
    ) -> ProviderConnectionSession:
        return self._transition_connection(
            connection,
            PROVIDER_CONNECTION_CLOSED,
            usage=usage,
        )

    def _store_connection(
        self,
        connection: ProviderConnectionSession,
    ) -> ProviderConnectionSession:
        self._last_connection = connection
        if connection.connection_status in PROVIDER_CONNECTION_TERMINAL_STATES:
            self._active_connections.pop(connection.provider_session_id, None)
        else:
            self._active_connections[connection.provider_session_id] = connection
        return connection

    def _connection_state_event(
        self,
        state: str,
        failure_status: str | None = None,
    ) -> dict[str, Any]:
        event = {
            "state": state,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        if failure_status:
            event["failure_status"] = failure_status
        return event

    def _connection_states(
        self,
        connection: ProviderConnectionSession,
    ) -> tuple[str, ...]:
        return tuple(
            str(entry.get("state"))
            for entry in connection.state_history
            if entry.get("state")
        )

    def _token_usage(
        self,
        connection: ProviderConnectionSession,
        usage: dict[str, Any] | None = None,
    ) -> tuple[int, int]:
        usage = usage or {}
        input_tokens = max(
            connection.input_tokens,
            self._usage_int(usage.get("input_tokens")),
        )
        output_tokens = max(
            connection.output_tokens,
            self._usage_int(usage.get("output_tokens")),
        )
        return input_tokens, output_tokens

    def _usage_int(self, value: Any) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    def _record_request_window(self) -> None:
        self._trim_request_window()
        self._request_window.append(datetime.now(timezone.utc))

    def _trim_request_window(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
        self._request_window = [at for at in self._request_window if at >= cutoff]

    def _result(
        self,
        status: str,
        success: bool,
        context: ProviderBridgeContext | None = None,
        request: ProviderBridgeRequest | None = None,
        provider_name: str | None = None,
        model: str | None = None,
        content: str | None = None,
        usage: dict[str, Any] | None = None,
        provider_duration_ms: int = 0,
        response_size_bytes: int = 0,
        reasons: list[str] | None = None,
        error: str | None = None,
        connection: ProviderConnectionSession | None = None,
        started: float | None = None,
        started_at: datetime | None = None,
    ) -> ProviderBridgeResult:
        self._trim_request_window()
        duration_ms = int((time.perf_counter() - started) * 1000) if started else 0
        finished_at = datetime.now(timezone.utc)
        execution = request.execution if request else None
        request_size = request.request_size_bytes() if request else 0
        connection_states = self._connection_states(connection) if connection else ()
        return ProviderBridgeResult(
            status=status,
            success=success,
            provider_name=(
                provider_name
                or (context.provider_name if context else None)
                or (request.provider_name if request else None)
            ),
            provider_session_id=(
                connection.provider_session_id
                if connection
                else (context.provider_session_id if context else None)
            ),
            connection_status=(
                connection.connection_status if connection else None
            ),
            failure_status=connection.failure_status if connection else None,
            connection_states=connection_states,
            model=model,
            content=content,
            request_id=context.request_id if context else None,
            execution_id=(
                context.execution_id
                if context
                else (execution.execution_id if execution else None)
            ),
            task_id=context.task_id if context else (execution.task_id if execution else None),
            started_at=started_at.isoformat() if started_at else None,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            provider_duration_ms=max(0, int(provider_duration_ms or 0)),
            usage=usage or {},
            active_provider_calls=self._active_calls,
            max_concurrent_provider_calls=self.max_concurrent_calls,
            max_requests_per_minute=self.max_requests_per_minute,
            requests_in_window=len(self._request_window),
            active_provider_sessions=len(self._active_connections),
            max_request_bytes=self.max_request_bytes,
            request_size_bytes=request_size,
            timeout_seconds=self.timeout_seconds,
            max_response_bytes=self.max_response_bytes,
            response_size_bytes=max(0, int(response_size_bytes or 0)),
            reasons=tuple(reasons or []),
            error=error,
            context=context,
            connection=connection,
        )

    def _log_result(self, result: ProviderBridgeResult) -> None:
        if result.status == "completed":
            logger.info(
                "provider_bridge: response received request_id=%s provider=%s duration_ms=%s",
                result.request_id,
                result.provider_name,
                result.duration_ms,
            )
            return
        if result.status in {"timeout", "error", "provider_error"}:
            logger.error(
                "provider_bridge: failure status=%s request_id=%s provider=%s reasons=%s error=%s",
                result.status,
                result.request_id,
                result.provider_name,
                ",".join(result.reasons),
                result.error,
            )
            return
        logger.warning(
            "provider_bridge: rejected status=%s request_id=%s provider=%s reasons=%s",
            result.status,
            result.request_id,
            result.provider_name,
            ",".join(result.reasons),
        )
