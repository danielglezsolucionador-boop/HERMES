"""
Runtime loop foundation for Hermes.

This loop only maintains runtime heartbeat and lifecycle state.
It does not pick up, lock, execute, or retry tasks.
"""
import asyncio
import logging
import time

from app.services.runtime_status import RuntimeStatus, runtime_status

logger = logging.getLogger(__name__)

DEFAULT_RUNTIME_LOOP_INTERVAL_SECONDS = 5.0
MIN_RUNTIME_LOOP_INTERVAL_SECONDS = 0.5
HEARTBEAT_LOG_EVERY = 60


class RuntimeLoop:
    def __init__(
        self,
        status: RuntimeStatus = runtime_status,
        interval_seconds: float = DEFAULT_RUNTIME_LOOP_INTERVAL_SECONDS,
        min_interval_seconds: float = MIN_RUNTIME_LOOP_INTERVAL_SECONDS,
        heartbeat_log_every: int = HEARTBEAT_LOG_EVERY,
    ) -> None:
        self.status = status
        self.interval_seconds = max(float(interval_seconds), float(min_interval_seconds))
        self.heartbeat_log_every = max(1, int(heartbeat_log_every))
        self._stop_requested = False
        self._paused = False

    def pause(self) -> None:
        self._paused = True
        self.status.mark_runtime_loop_paused()
        logger.info("runtime_loop: paused")

    def resume(self) -> None:
        self._paused = False
        logger.info("runtime_loop: resumed")

    def request_stop(self, reason: str = "stop_requested") -> None:
        self._stop_requested = True
        self.status.request_runtime_loop_stop(reason)
        logger.info("runtime_loop: stop requested reason=%s", reason)

    async def _cycle(self) -> str:
        if self._paused:
            self.status.mark_runtime_loop_paused()
            return "paused"
        return "active"

    async def run(self) -> None:
        self._stop_requested = False
        self.status.mark_runtime_loop_started(self.interval_seconds)
        logger.info(
            "runtime_loop: started interval_seconds=%s",
            self.interval_seconds,
        )

        stop_reason = "stopped"
        try:
            while not self._stop_requested:
                cycle_started = time.perf_counter()
                try:
                    state = await self._cycle()
                except asyncio.CancelledError:
                    stop_reason = "cancelled"
                    logger.info("runtime_loop: cancelled")
                    raise
                except Exception as exc:
                    state = "recovering"
                    logger.error("runtime_loop: cycle error survived error=%s", exc)

                duration_ms = int((time.perf_counter() - cycle_started) * 1000)
                self.status.mark_runtime_loop_heartbeat(
                    state=state,
                    cycle_duration_ms=duration_ms,
                )
                iteration = self.status.runtime_loop_iteration
                if iteration == 1 or iteration % self.heartbeat_log_every == 0:
                    logger.info(
                        "runtime_loop: heartbeat iteration=%s state=%s duration_ms=%s",
                        iteration,
                        state,
                        duration_ms,
                    )

                await asyncio.sleep(self.interval_seconds)
        finally:
            if self._stop_requested:
                stop_reason = self.status.runtime_loop_stop_reason or "stop_requested"
            self.status.mark_runtime_loop_stopped(stop_reason)
            logger.info("runtime_loop: stopped reason=%s", stop_reason)


runtime_loop = RuntimeLoop()
