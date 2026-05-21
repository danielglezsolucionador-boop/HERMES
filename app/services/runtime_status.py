"""
In-memory runtime status for the local runner process.
PostgreSQL remains the source of truth for tasks.
"""
from datetime import datetime, timezone


class RuntimeStatus:
    def __init__(self):
        self.runner_started_at: datetime | None = None
        self.last_loop_at: datetime | None = None
        self.last_task_started_at: datetime | None = None
        self.last_task_completed_at: datetime | None = None
        self.current_task_id: str | None = None
        self.current_task_title: str | None = None
        self.total_processed = 0
        self.total_success = 0
        self.total_failed = 0
        self.runner_alive = False
        self.total_ai_requests = 0
        self.ai_success_requests = 0
        self.ai_failed_requests = 0
        self.total_ai_duration_ms = 0
        self.total_ai_provider_duration_ms = 0
        self.total_ai_context_build_ms = 0
        self.last_ai_provider: str | None = None
        self.last_ai_model: str | None = None
        self.last_ai_error: str | None = None
        self.last_ai_request_at: datetime | None = None
        self.telegram_messages_processed = 0
        self.telegram_messages_total = 0
        self.telegram_messages_failed = 0
        self.telegram_last_message_at: datetime | None = None
        self.telegram_last_error: str | None = None
        self.runtime_loop_started_at: datetime | None = None
        self.runtime_loop_last_heartbeat_at: datetime | None = None
        self.runtime_loop_last_cycle_duration_ms = 0
        self.runtime_loop_iteration = 0
        self.runtime_loop_alive = False
        self.runtime_loop_state = "stopped"
        self.runtime_loop_stop_requested = False
        self.runtime_loop_stop_reason: str | None = None
        self.runtime_loop_interval_seconds = 0.0
        self.polling_started_at: datetime | None = None
        self.last_poll_time: datetime | None = None
        self.polling_iteration = 0
        self.tasks_detected = 0
        self.polling_status = "stopped"
        self.polling_interval_seconds = 0.0
        self.polling_last_duration_ms = 0
        self.polling_errors = 0
        self.polling_last_error: str | None = None
        self.discovery_started_at: datetime | None = None
        self.last_discovery_at: datetime | None = None
        self.discovery_iteration = 0
        self.discovery_status = "stopped"
        self.discovery_interval_seconds = 0.0
        self.discovery_last_duration_ms = 0
        self.discovery_errors = 0
        self.discovery_last_error: str | None = None
        self.discovered_tasks = 0
        self.discovery_limit = 0
        self.discovery_max_payload_bytes = 0
        self.discovery_query_timeout_seconds = 0.0
        self.discovery_ignored_count = 0
        self.discovery_ignored_reasons: dict[str, int] = {}
        self.discovery_filters: dict[str, str] = {}
        self.discovery_ordering: list[str] = []
        self.discovery_candidates: list[dict] = []
        self.claiming_started_at: datetime | None = None
        self.last_claiming_at: datetime | None = None
        self.claiming_iteration = 0
        self.claiming_enabled = False
        self.claiming_status = "stopped"
        self.claiming_interval_seconds = 0.0
        self.claiming_last_duration_ms = 0
        self.claiming_errors = 0
        self.claiming_last_error: str | None = None
        self.claims_attempted = 0
        self.claims_succeeded = 0
        self.claims_conflicted = 0
        self.claims_rejected = 0
        self.active_claims = 0
        self.stale_claims = 0
        self.max_concurrent_claims = 0
        self.max_attempts_per_cycle = 0
        self.max_task_attempts = 0
        self.min_claim_interval_seconds = 0.0
        self.stale_claim_after_seconds = 0
        self.max_stale_claims = 0
        self.claiming_runner_id: str | None = None
        self.claiming_runtime_id: str | None = None
        self.last_claimed_task: dict | None = None
        self.pickup_safety_started_at: datetime | None = None
        self.last_pickup_safety_at: datetime | None = None
        self.pickup_safety_iteration = 0
        self.pickup_safety_enabled = False
        self.pickup_safety_status = "stopped"
        self.pickup_safety_interval_seconds = 0.0
        self.pickup_safety_last_duration_ms = 0
        self.pickup_safety_errors = 0
        self.pickup_safety_last_error: str | None = None
        self.pickup_safety_allows_pickup = True
        self.pickup_safety_duplicate_prevention = True
        self.pickup_safety_race_condition_controlled = True
        self.pickup_safety_ownership_consistent = True
        self.pickup_safety_runtime_consistent = True
        self.pickup_safety_retry_allowed = True
        self.pickup_safety_active_claims = 0
        self.pickup_safety_stale_claims = 0
        self.pickup_safety_orphaned_claims = 0
        self.pickup_safety_foreign_runtime_claims = 0
        self.pickup_safety_invalid_claims = 0
        self.pickup_safety_max_concurrent_claims = 0
        self.pickup_safety_max_stale_claims = 0
        self.pickup_safety_max_orphaned_claims = 0
        self.pickup_safety_max_invalid_claims = 0
        self.pickup_safety_max_foreign_runtime_claims = 0
        self.pickup_safety_retry_attempts = 0
        self.pickup_safety_max_retries = 0
        self.pickup_safety_retry_window_seconds = 0
        self.pickup_safety_reasons: list[str] = []
        self.pickup_safety_runner_id: str | None = None
        self.pickup_safety_runtime_id: str | None = None
        self.task_execution_started_at: datetime | None = None
        self.last_execution_at: datetime | None = None
        self.execution_iteration = 0
        self.execution_enabled = False
        self.execution_status = "stopped"
        self.execution_interval_seconds = 0.0
        self.execution_last_duration_ms = 0
        self.execution_errors = 0
        self.execution_last_error: str | None = None
        self.executions_prepared = 0
        self.executions_started = 0
        self.executions_completed = 0
        self.executions_rejected = 0
        self.active_executions = 0
        self.max_concurrent_executions = 0
        self.max_execution_duration_seconds = 0
        self.max_runtime_load = 0.0
        self.runtime_load: float | None = None
        self.max_execution_memory_mb = 0
        self.execution_memory_usage_mb: float | None = None
        self.last_execution_id: str | None = None
        self.last_execution_state: str | None = None
        self.last_execution_task_id: str | None = None
        self.last_execution_task_title: str | None = None
        self.last_execution_started_at: str | None = None
        self.last_execution_finished_at: str | None = None
        self.last_execution_duration_ms = 0
        self.execution_runtime_owner: str | None = None
        self.execution_reasons: list[str] = []
        self.execution_session_started_at: datetime | None = None
        self.last_execution_session_at: datetime | None = None
        self.execution_session_iteration = 0
        self.execution_session_enabled = False
        self.execution_session_status = "stopped"
        self.execution_session_state: str | None = None
        self.execution_session_interval_seconds = 0.0
        self.execution_session_last_duration_ms = 0
        self.execution_session_errors = 0
        self.execution_session_last_error: str | None = None
        self.execution_session_runtime_protected = True
        self.execution_session_active_sessions = 0
        self.execution_session_max_active_sessions = 0
        self.execution_session_max_log_entries = 0
        self.execution_session_recovery_available = False
        self.execution_session_runtime_owner: str | None = None
        self.last_execution_session_id: str | None = None
        self.last_execution_session_task_id: str | None = None
        self.last_execution_session_phase_id: str | None = None
        self.last_execution_session_audit_status: str | None = None
        self.last_execution_session_checkpoint: str | None = None
        self.last_execution_session_action: str | None = None
        self.last_execution_session_file_modified: str | None = None
        self.last_execution_session_result: str | None = None
        self.last_execution_session_error_detail: str | None = None
        self.last_execution_session_audit: str | None = None
        self.execution_session_modified_files: list[str] = []
        self.last_execution_session_human_approval_status: str | None = None
        self.execution_session_context_snapshot: dict | None = None
        self.execution_session_context_recovery_available = False
        self.execution_session_log_count = 0
        self.execution_session_last_log: dict | None = None
        self.last_execution_session_previous_state: str | None = None
        self.last_execution_session_transition: str | None = None
        self.execution_session_transition_allowed = True
        self.execution_session_blocking_detected = False
        self.execution_session_blocking_reasons: list[str] = []
        self.last_execution_session_lifecycle_stage: str | None = None
        self.last_execution_session_lifecycle_transition: str | None = None
        self.execution_session_lifecycle_transition_allowed = True
        self.execution_session_snapshot: dict | None = None
        self.execution_session_reasons: list[str] = []
        self.execution_safety_started_at: datetime | None = None
        self.last_execution_safety_at: datetime | None = None
        self.execution_safety_iteration = 0
        self.execution_safety_enabled = False
        self.execution_safety_status = "stopped"
        self.execution_safety_interval_seconds = 0.0
        self.execution_safety_last_duration_ms = 0
        self.execution_safety_errors = 0
        self.execution_safety_last_error: str | None = None
        self.execution_safety_allows_execution = True
        self.execution_safety_runtime_protected = True
        self.execution_conflict_detected = False
        self.execution_timeout_detected = False
        self.execution_provider_failure_detected = False
        self.execution_retry_allowed = True
        self.execution_retry_attempts = 0
        self.execution_max_retries = 0
        self.execution_safety_active_executions = 0
        self.execution_safety_max_concurrent_executions = 0
        self.execution_safety_runtime_load: float | None = None
        self.execution_safety_max_runtime_load = 0.0
        self.execution_safety_memory_usage_mb: float | None = None
        self.execution_safety_max_memory_mb = 0
        self.execution_safety_active_provider_calls = 0
        self.execution_safety_max_concurrent_provider_calls = 0
        self.execution_safety_provider_status: str | None = None
        self.execution_safety_execution_status: str | None = None
        self.execution_safety_execution_id: str | None = None
        self.execution_safety_task_id: str | None = None
        self.execution_safety_checked_at: str | None = None
        self.execution_safety_reasons: list[str] = []
        self.timeout_control_started_at: datetime | None = None
        self.last_timeout_control_at: datetime | None = None
        self.timeout_control_iteration = 0
        self.timeout_control_enabled = False
        self.timeout_control_status = "stopped"
        self.timeout_state: str | None = None
        self.timeout_control_interval_seconds = 0.0
        self.timeout_control_last_duration_ms = 0
        self.timeout_control_errors = 0
        self.timeout_control_last_error: str | None = None
        self.timeout_checks_passed = 0
        self.timeout_checks_rejected = 0
        self.timeout_checks_failed = 0
        self.timeouts_detected = 0
        self.timeout_monitoring_allowed = True
        self.timeout_runtime_protected = True
        self.timeout_detected = False
        self.timeout_registered = False
        self.timeout_duration_tracking = False
        self.timeout_linkage_valid = True
        self.timeout_ownership_consistent = True
        self.active_timeout_checks = 0
        self.max_concurrent_timeout_checks = 0
        self.runtime_timeout_load: float | None = None
        self.max_runtime_timeout_load = 0.0
        self.max_timeout_tracking_duration_ms = 0
        self.max_timeout_check_duration_ms = 0
        self.last_timeout_id: str | None = None
        self.last_timeout_execution_id: str | None = None
        self.last_timeout_task_id: str | None = None
        self.last_timeout_runtime_id: str | None = None
        self.last_timeout_runtime_owner: str | None = None
        self.last_timeout_execution_state: str | None = None
        self.last_timeout_execution_started_at: str | None = None
        self.last_timeout_detected_at: str | None = None
        self.last_timeout_checked_at: str | None = None
        self.timeout_execution_duration_ms = 0
        self.timeout_threshold_ms = 0
        self.timeout_control_metadata: dict = {}
        self.timeout_control_reasons: list[str] = []
        self.retry_control_started_at: datetime | None = None
        self.last_retry_control_at: datetime | None = None
        self.retry_control_iteration = 0
        self.retry_control_enabled = False
        self.retry_control_status = "stopped"
        self.retry_state: str | None = None
        self.retry_control_interval_seconds = 0.0
        self.retry_control_last_duration_ms = 0
        self.retry_control_errors = 0
        self.retry_control_last_error: str | None = None
        self.retries_registered = 0
        self.retries_started = 0
        self.retries_completed = 0
        self.retries_rejected = 0
        self.retries_failed = 0
        self.retry_allowed = True
        self.retry_runtime_protected = True
        self.retry_linkage_valid = True
        self.retry_ownership_consistent = True
        self.retry_threshold_valid = True
        self.retry_provider_available = True
        self.active_retries = 0
        self.max_concurrent_retries = 0
        self.runtime_retry_load: float | None = None
        self.max_runtime_retry_load = 0.0
        self.max_retry_attempts = 0
        self.max_retry_duration_ms = 0
        self.max_retry_overhead_ms = 0
        self.last_retry_id: str | None = None
        self.last_retry_execution_id: str | None = None
        self.last_retry_task_id: str | None = None
        self.last_retry_runner_id: str | None = None
        self.last_retry_runtime_id: str | None = None
        self.last_retry_runtime_owner: str | None = None
        self.last_retry_execution_state: str | None = None
        self.last_retry_task_status: str | None = None
        self.last_retry_provider_status: str | None = None
        self.last_retry_attempt = 0
        self.last_retry_threshold = 0
        self.last_retry_reason: str | None = None
        self.last_retry_started_at: str | None = None
        self.last_retry_completed_at: str | None = None
        self.last_retry_duration_ms = 0
        self.retry_control_metadata: dict = {}
        self.retry_control_reasons: list[str] = []
        self.orchestration_started_at: datetime | None = None
        self.last_orchestration_at: datetime | None = None
        self.orchestration_iteration = 0
        self.orchestration_enabled = False
        self.orchestration_status = "stopped"
        self.orchestration_state: str | None = None
        self.dependency_state: str | None = None
        self.orchestration_interval_seconds = 0.0
        self.orchestration_last_duration_ms = 0
        self.orchestration_errors = 0
        self.orchestration_last_error: str | None = None
        self.orchestrations_registered = 0
        self.orchestrations_started = 0
        self.orchestrations_completed = 0
        self.orchestrations_released = 0
        self.orchestrations_rejected = 0
        self.orchestrations_failed = 0
        self.coordination_allowed = True
        self.orchestration_runtime_protected = True
        self.orchestration_conflict_detected = False
        self.orchestration_linkage_valid = True
        self.orchestration_ownership_consistent = True
        self.orchestration_dependency_valid = True
        self.active_orchestrations = 0
        self.max_active_orchestrations = 0
        self.runtime_orchestration_load: float | None = None
        self.max_orchestration_load = 0.0
        self.max_execution_dependencies = 0
        self.max_dependency_chain = 0
        self.max_orchestration_duration_ms = 0
        self.max_coordination_overhead_ms = 0
        self.last_orchestration_id: str | None = None
        self.last_orchestration_execution_id: str | None = None
        self.last_orchestration_task_id: str | None = None
        self.last_orchestration_runner_id: str | None = None
        self.last_orchestration_runtime_id: str | None = None
        self.last_orchestration_runtime_owner: str | None = None
        self.last_orchestration_execution_state: str | None = None
        self.last_orchestration_task_status: str | None = None
        self.last_orchestration_execution_order = 0
        self.last_orchestration_dependency_count = 0
        self.last_coordination_started_at: str | None = None
        self.last_coordination_completed_at: str | None = None
        self.last_coordination_duration_ms = 0
        self.orchestration_dependencies: list[dict] = []
        self.orchestration_metadata: dict = {}
        self.orchestration_reasons: list[str] = []
        self.orchestration_safety_started_at: datetime | None = None
        self.last_orchestration_safety_at: datetime | None = None
        self.orchestration_safety_iteration = 0
        self.orchestration_safety_enabled = False
        self.orchestration_safety_status = "stopped"
        self.orchestration_safety_state: str | None = None
        self.orchestration_safety_interval_seconds = 0.0
        self.orchestration_safety_last_duration_ms = 0
        self.orchestration_safety_errors = 0
        self.orchestration_safety_last_error: str | None = None
        self.orchestration_safety_allows_orchestration = True
        self.orchestration_safety_runtime_protected = True
        self.orchestration_safety_conflict_detected = False
        self.orchestration_safety_dependency_corruption_detected = False
        self.orchestration_safety_sequencing_violation_detected = False
        self.orchestration_safety_runaway_detected = False
        self.orchestration_safety_timeout_detected = False
        self.orchestration_safety_retry_allowed = True
        self.orchestration_safety_retry_attempts = 0
        self.orchestration_safety_max_retries = 0
        self.orchestration_safety_active_orchestrations = 0
        self.orchestration_safety_max_active_orchestrations = 0
        self.orchestration_safety_runtime_load: float | None = None
        self.orchestration_safety_max_runtime_load = 0.0
        self.orchestration_safety_coordination_duration_ms = 0
        self.orchestration_safety_max_duration_ms = 0
        self.orchestration_safety_coordination_overhead_ms = 0
        self.orchestration_safety_max_overhead_ms = 0
        self.last_orchestration_safety_id: str | None = None
        self.orchestration_safety_coordination_id: str | None = None
        self.orchestration_safety_execution_id: str | None = None
        self.orchestration_safety_task_id: str | None = None
        self.orchestration_safety_runtime_owner: str | None = None
        self.orchestration_safety_dependencies: list[dict] = []
        self.orchestration_safety_metadata: dict = {}
        self.orchestration_safety_reasons: list[str] = []
        self.provider_bridge_started_at: datetime | None = None
        self.last_provider_bridge_at: datetime | None = None
        self.provider_bridge_iteration = 0
        self.provider_bridge_enabled = False
        self.provider_bridge_status = "stopped"
        self.provider_bridge_interval_seconds = 0.0
        self.provider_bridge_last_duration_ms = 0
        self.provider_bridge_errors = 0
        self.provider_bridge_last_error: str | None = None
        self.provider_requests_completed = 0
        self.provider_requests_rejected = 0
        self.provider_requests_failed = 0
        self.provider_timeouts = 0
        self.provider_invalid_responses = 0
        self.active_provider_calls = 0
        self.active_provider_sessions = 0
        self.max_concurrent_provider_calls = 0
        self.max_provider_requests_per_minute = 0
        self.provider_requests_in_window = 0
        self.max_provider_request_bytes = 0
        self.provider_request_size_bytes = 0
        self.provider_timeout_seconds = 0.0
        self.max_provider_response_bytes = 0
        self.provider_response_size_bytes = 0
        self.provider_name: str | None = None
        self.provider_session_id: str | None = None
        self.provider_connection_status: str | None = None
        self.provider_failure_status: str | None = None
        self.provider_connection_states: list[str] = []
        self.provider_model: str | None = None
        self.provider_request_id: str | None = None
        self.provider_execution_id: str | None = None
        self.provider_task_id: str | None = None
        self.provider_started_at: str | None = None
        self.provider_finished_at: str | None = None
        self.provider_duration_ms = 0
        self.provider_usage: dict = {}
        self.provider_input_tokens = 0
        self.provider_output_tokens = 0
        self.provider_total_tokens = 0
        self.provider_bridge_reasons: list[str] = []
        self.response_ingestion_started_at: datetime | None = None
        self.last_response_ingestion_at: datetime | None = None
        self.response_ingestion_iteration = 0
        self.response_ingestion_enabled = False
        self.response_ingestion_status = "stopped"
        self.response_ingestion_state: str | None = None
        self.response_ingestion_interval_seconds = 0.0
        self.response_ingestion_last_duration_ms = 0
        self.response_ingestion_errors = 0
        self.response_ingestion_last_error: str | None = None
        self.responses_received = 0
        self.responses_ingested = 0
        self.responses_rejected = 0
        self.responses_failed = 0
        self.active_response_ingestions = 0
        self.max_concurrent_response_ingestions = 0
        self.max_response_ingestion_bytes = 0
        self.response_ingestion_size_bytes = 0
        self.max_response_ingestion_duration_ms = 0
        self.response_ingestion_runtime_load: float | None = None
        self.max_response_ingestion_runtime_load = 0.0
        self.last_response_id: str | None = None
        self.last_response_execution_id: str | None = None
        self.last_response_task_id: str | None = None
        self.last_response_runtime_id: str | None = None
        self.last_response_execution_owner: str | None = None
        self.last_response_provider_source: str | None = None
        self.last_response_provider_request_id: str | None = None
        self.last_response_model: str | None = None
        self.last_response_received_at: str | None = None
        self.last_response_started_at: str | None = None
        self.last_response_finished_at: str | None = None
        self.response_storage_prepared = False
        self.response_ingestion_metadata: dict = {}
        self.response_ingestion_reasons: list[str] = []
        self.response_validation_started_at: datetime | None = None
        self.last_response_validation_at: datetime | None = None
        self.response_validation_iteration = 0
        self.response_validation_enabled = False
        self.response_validation_status = "stopped"
        self.response_validation_state: str | None = None
        self.response_validation_interval_seconds = 0.0
        self.response_validation_last_duration_ms = 0
        self.response_validation_errors = 0
        self.response_validation_last_error: str | None = None
        self.responses_validated = 0
        self.responses_validation_rejected = 0
        self.responses_validation_failed = 0
        self.active_response_validations = 0
        self.max_concurrent_response_validations = 0
        self.max_response_validation_payload_bytes = 0
        self.response_validation_payload_size_bytes = 0
        self.max_response_validation_duration_ms = 0
        self.response_validation_runtime_load: float | None = None
        self.max_response_validation_runtime_load = 0.0
        self.last_validation_id: str | None = None
        self.last_validation_execution_id: str | None = None
        self.last_validation_task_id: str | None = None
        self.last_validation_runtime_id: str | None = None
        self.last_validation_execution_owner: str | None = None
        self.last_validation_provider_source: str | None = None
        self.last_validation_provider_request_id: str | None = None
        self.last_validation_model: str | None = None
        self.last_validation_validated_at: str | None = None
        self.last_validation_started_at: str | None = None
        self.last_validation_finished_at: str | None = None
        self.response_validation_metadata: dict = {}
        self.response_validation_reasons: list[str] = []
        self.response_safety_started_at: datetime | None = None
        self.last_response_safety_at: datetime | None = None
        self.response_safety_iteration = 0
        self.response_safety_enabled = False
        self.response_safety_status = "stopped"
        self.response_safety_state: str | None = None
        self.response_safety_interval_seconds = 0.0
        self.response_safety_last_duration_ms = 0
        self.response_safety_errors = 0
        self.response_safety_last_error: str | None = None
        self.responses_safety_passed = 0
        self.responses_safety_blocked = 0
        self.responses_safety_failed = 0
        self.active_response_safety_checks = 0
        self.max_concurrent_response_safety_checks = 0
        self.max_response_safety_payload_bytes = 0
        self.response_safety_payload_size_bytes = 0
        self.max_response_safety_duration_ms = 0
        self.response_safety_runtime_load: float | None = None
        self.max_response_safety_runtime_load = 0.0
        self.last_safety_id: str | None = None
        self.last_safety_execution_id: str | None = None
        self.last_safety_task_id: str | None = None
        self.last_safety_runtime_id: str | None = None
        self.last_safety_execution_owner: str | None = None
        self.last_safety_provider_source: str | None = None
        self.last_safety_provider_request_id: str | None = None
        self.last_safety_model: str | None = None
        self.last_safety_checked_at: str | None = None
        self.last_safety_started_at: str | None = None
        self.last_safety_finished_at: str | None = None
        self.response_safety_allows_response = True
        self.response_safety_runtime_protected = True
        self.response_safety_corrupted_detected = False
        self.response_safety_poisoning_detected = False
        self.response_safety_timeout_detected = False
        self.response_safety_provider_failure_detected = False
        self.response_safety_retry_allowed = True
        self.response_safety_retry_attempts = 0
        self.response_safety_max_validation_retries = 0
        self.response_safety_metadata: dict = {}
        self.response_safety_reasons: list[str] = []
        self.runtime_safe = True
        self.consecutive_errors = 0
        self.degraded_state = False
        self.safety_stop_reason: str | None = None
        self.safety_events: list[dict] = []
        self.safety_event_limit = 20

    def mark_started(self) -> None:
        self.runner_started_at = datetime.now(timezone.utc)
        self.runner_alive = True

    def mark_loop(self) -> None:
        self.last_loop_at = datetime.now(timezone.utc)

    def mark_task_started(self, task_id: str, task_title: str) -> None:
        self.current_task_id = task_id
        self.current_task_title = task_title
        self.last_task_started_at = datetime.now(timezone.utc)

    def mark_task_done(self) -> None:
        self.last_task_completed_at = datetime.now(timezone.utc)
        self.current_task_id = None
        self.current_task_title = None
        self.total_processed += 1
        self.total_success += 1

    def mark_task_failed(self) -> None:
        self.last_task_completed_at = datetime.now(timezone.utc)
        self.current_task_id = None
        self.current_task_title = None
        self.total_processed += 1
        self.total_failed += 1

    def mark_ai_request(
        self,
        success: bool,
        duration_ms: int,
        provider: str | None = None,
        model: str | None = None,
        provider_ms: int = 0,
        context_build_ms: int = 0,
        error: str | None = None,
    ) -> None:
        safe_duration = max(0, int(duration_ms or 0))
        safe_provider_ms = max(0, int(provider_ms or 0))
        safe_context_ms = max(0, int(context_build_ms or 0))

        self.last_ai_request_at = datetime.now(timezone.utc)
        self.total_ai_requests += 1
        if success:
            self.ai_success_requests += 1
            self.last_ai_error = None
        else:
            self.ai_failed_requests += 1
            self.last_ai_error = error or "unknown_ai_error"

        self.total_ai_duration_ms += safe_duration
        self.total_ai_provider_duration_ms += safe_provider_ms
        self.total_ai_context_build_ms += safe_context_ms
        self.last_ai_provider = provider
        self.last_ai_model = model

    def mark_telegram_message_processed(self) -> None:
        self.mark_telegram_message(success=True)

    def mark_telegram_message(
        self,
        success: bool,
        error: str | None = None,
    ) -> None:
        self.telegram_messages_total += 1
        self.telegram_messages_processed += 1
        self.telegram_last_message_at = datetime.now(timezone.utc)
        if success:
            self.telegram_last_error = None
            return
        self.telegram_messages_failed += 1
        self.telegram_last_error = error or "unknown_telegram_error"

    def mark_runtime_loop_started(self, interval_seconds: float) -> None:
        self.runtime_loop_started_at = datetime.now(timezone.utc)
        self.runtime_loop_last_heartbeat_at = None
        self.runtime_loop_last_cycle_duration_ms = 0
        self.runtime_loop_iteration = 0
        self.runtime_loop_alive = True
        self.runtime_loop_state = "active"
        self.runtime_loop_stop_requested = False
        self.runtime_loop_stop_reason = None
        self.runtime_loop_interval_seconds = interval_seconds
        self.runtime_safe = True
        self.consecutive_errors = 0
        self.degraded_state = False
        self.safety_stop_reason = None
        self.safety_events = []

    def mark_runtime_loop_heartbeat(
        self,
        state: str = "active",
        cycle_duration_ms: int = 0,
    ) -> None:
        self.runtime_loop_last_heartbeat_at = datetime.now(timezone.utc)
        self.runtime_loop_last_cycle_duration_ms = max(0, int(cycle_duration_ms or 0))
        self.runtime_loop_iteration += 1
        self.runtime_loop_alive = True
        self.runtime_loop_state = state
        self.runtime_loop_stop_requested = False

    def mark_runtime_loop_paused(self) -> None:
        self.runtime_loop_last_heartbeat_at = datetime.now(timezone.utc)
        self.runtime_loop_alive = True
        self.runtime_loop_state = "paused"

    def request_runtime_loop_stop(self, reason: str = "stop_requested") -> None:
        self.runtime_loop_stop_requested = True
        self.runtime_loop_stop_reason = reason

    def mark_runtime_loop_stopped(self, reason: str = "stopped") -> None:
        self.runtime_loop_alive = False
        self.runtime_loop_state = "stopped"
        self.runtime_loop_stop_requested = True
        self.runtime_loop_stop_reason = reason
        self.polling_status = "stopped"
        self.discovery_status = "stopped"
        self.claiming_status = "stopped"
        self.pickup_safety_status = "stopped"
        self.execution_status = "stopped"
        self.execution_session_status = "stopped"
        self.execution_safety_status = "stopped"
        self.timeout_control_status = "stopped"
        self.retry_control_status = "stopped"
        self.orchestration_status = "stopped"
        self.orchestration_safety_status = "stopped"
        self.provider_bridge_status = "stopped"
        self.response_ingestion_status = "stopped"
        self.response_validation_status = "stopped"
        self.response_safety_status = "stopped"

    def configure_safety_event_limit(self, limit: int) -> None:
        self.safety_event_limit = max(1, int(limit or 1))
        self.safety_events = self.safety_events[-self.safety_event_limit :]

    def record_safety_event(
        self,
        event: str,
        severity: str = "info",
        detail: str | None = None,
    ) -> None:
        payload = {
            "at": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "severity": severity,
            "detail": detail,
            "consecutive_errors": self.consecutive_errors,
        }
        self.safety_events.append(payload)
        self.safety_events = self.safety_events[-self.safety_event_limit :]

    def mark_runtime_loop_cycle_success(self) -> None:
        if self.consecutive_errors:
            self.record_safety_event(
                "runtime_recovered",
                severity="info",
                detail="cycle_completed_after_error",
            )
        self.consecutive_errors = 0
        if self.runtime_safe:
            self.degraded_state = False

    def mark_runtime_loop_error(
        self,
        error: str,
        degraded_threshold: int,
        max_consecutive_errors: int,
    ) -> dict:
        self.consecutive_errors += 1
        detail = error or "unknown_runtime_loop_error"
        degraded_started = False
        should_stop = False
        if self.consecutive_errors >= degraded_threshold and not self.degraded_state:
            self.degraded_state = True
            degraded_started = True
            self.record_safety_event(
                "runtime_degraded",
                severity="warning",
                detail=detail,
            )
        if self.consecutive_errors >= max_consecutive_errors:
            self.runtime_safe = False
            self.safety_stop_reason = "max_consecutive_errors"
            should_stop = True
            self.record_safety_event(
                "runtime_safety_stop",
                severity="critical",
                detail=detail,
            )
        return {
            "degraded_started": degraded_started,
            "should_stop": should_stop,
        }

    def mark_polling_started(self, interval_seconds: float) -> None:
        self.polling_started_at = datetime.now(timezone.utc)
        self.polling_status = "active"
        self.polling_interval_seconds = interval_seconds
        self.polling_last_error = None

    def mark_polling_completed(
        self,
        tasks_detected: int,
        duration_ms: int,
    ) -> None:
        self.last_poll_time = datetime.now(timezone.utc)
        self.polling_iteration += 1
        self.tasks_detected = max(0, int(tasks_detected or 0))
        self.polling_last_duration_ms = max(0, int(duration_ms or 0))
        self.polling_status = (
            "tasks_detected" if self.tasks_detected > 0 else "idle"
        )
        self.polling_last_error = None

    def mark_polling_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_poll_time = datetime.now(timezone.utc)
        self.polling_iteration += 1
        self.polling_last_duration_ms = max(0, int(duration_ms or 0))
        self.polling_errors += 1
        self.polling_status = "error"
        self.polling_last_error = error or "unknown_polling_error"

    def mark_task_discovery_started(self, interval_seconds: float) -> None:
        self.discovery_started_at = datetime.now(timezone.utc)
        self.discovery_status = "active"
        self.discovery_interval_seconds = interval_seconds
        self.discovery_last_error = None

    def mark_task_discovery_completed(self, result: dict) -> None:
        self.last_discovery_at = datetime.now(timezone.utc)
        self.discovery_iteration += 1
        self.discovery_status = result.get("status") or "unknown"
        self.discovered_tasks = max(0, int(result.get("discovered_count") or 0))
        self.discovery_last_duration_ms = max(0, int(result.get("duration_ms") or 0))
        self.discovery_limit = max(0, int(result.get("limit") or 0))
        self.discovery_max_payload_bytes = max(
            0,
            int(result.get("max_payload_bytes") or 0),
        )
        self.discovery_query_timeout_seconds = max(
            0.0,
            float(result.get("query_timeout_seconds") or 0.0),
        )
        self.discovery_ignored_count = max(
            0,
            int(result.get("ignored_count") or 0),
        )
        ignored_reasons = result.get("ignored_reasons") or {}
        self.discovery_ignored_reasons = {
            str(reason): max(0, int(count or 0))
            for reason, count in ignored_reasons.items()
        }
        self.discovery_filters = {
            str(name): str(value)
            for name, value in (result.get("filters") or {}).items()
        }
        self.discovery_ordering = [
            str(ordering) for ordering in (result.get("ordering") or [])
        ]
        self.discovery_candidates = list(result.get("candidates") or [])
        self.discovery_last_error = None

    def mark_task_discovery_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_discovery_at = datetime.now(timezone.utc)
        self.discovery_iteration += 1
        self.discovery_last_duration_ms = max(0, int(duration_ms or 0))
        self.discovery_errors += 1
        self.discovery_status = "error"
        self.discovery_last_error = error or "unknown_discovery_error"

    def mark_task_claiming_started(
        self,
        enabled: bool,
        interval_seconds: float,
    ) -> None:
        self.claiming_started_at = datetime.now(timezone.utc)
        self.claiming_enabled = bool(enabled)
        self.claiming_status = "active" if enabled else "disabled"
        self.claiming_interval_seconds = interval_seconds
        self.claiming_last_error = None

    def mark_task_claiming_completed(self, result: dict) -> None:
        self.last_claiming_at = datetime.now(timezone.utc)
        self.claiming_iteration += 1
        self.claiming_status = result.get("status") or "unknown"
        self.claiming_last_duration_ms = max(0, int(result.get("duration_ms") or 0))
        self.claims_attempted += max(0, int(result.get("attempted_count") or 0))
        self.claims_succeeded += max(0, int(result.get("claimed_count") or 0))
        self.claims_conflicted += max(0, int(result.get("conflict_count") or 0))
        self.claims_rejected += max(0, int(result.get("rejected_count") or 0))
        self.active_claims = max(0, int(result.get("active_claims") or 0))
        self.stale_claims = max(0, int(result.get("stale_claims") or 0))
        self.max_concurrent_claims = max(
            0,
            int(result.get("max_concurrent_claims") or 0),
        )
        self.max_attempts_per_cycle = max(
            0,
            int(result.get("max_attempts_per_cycle") or 0),
        )
        self.max_task_attempts = max(0, int(result.get("max_task_attempts") or 0))
        self.min_claim_interval_seconds = max(
            0.0,
            float(result.get("min_interval_seconds") or 0.0),
        )
        self.stale_claim_after_seconds = max(
            0,
            int(result.get("stale_after_seconds") or 0),
        )
        self.max_stale_claims = max(0, int(result.get("max_stale_claims") or 0))
        self.claiming_runner_id = result.get("runner_id")
        self.claiming_runtime_id = result.get("runtime_id")
        if result.get("task_id"):
            self.last_claimed_task = {
                "id": result.get("task_id"),
                "title": result.get("task_title"),
                "claimed_at": result.get("claimed_at"),
                "claim_state": result.get("claim_state"),
            }
        self.claiming_last_error = result.get("error")

    def mark_task_claiming_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_claiming_at = datetime.now(timezone.utc)
        self.claiming_iteration += 1
        self.claiming_last_duration_ms = max(0, int(duration_ms or 0))
        self.claiming_errors += 1
        self.claiming_status = "error"
        self.claiming_last_error = error or "unknown_claiming_error"

    def mark_pickup_safety_started(
        self,
        enabled: bool,
        interval_seconds: float,
    ) -> None:
        self.pickup_safety_started_at = datetime.now(timezone.utc)
        self.pickup_safety_enabled = bool(enabled)
        self.pickup_safety_status = "active" if enabled else "disabled"
        self.pickup_safety_interval_seconds = interval_seconds
        self.pickup_safety_last_error = None

    def mark_pickup_safety_completed(self, result: dict) -> None:
        self.last_pickup_safety_at = datetime.now(timezone.utc)
        self.pickup_safety_iteration += 1
        self.pickup_safety_status = result.get("status") or "unknown"
        self.pickup_safety_last_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.pickup_safety_allows_pickup = bool(result.get("allows_pickup"))
        self.pickup_safety_duplicate_prevention = bool(
            result.get("duplicate_prevention")
        )
        self.pickup_safety_race_condition_controlled = bool(
            result.get("race_condition_controlled")
        )
        self.pickup_safety_ownership_consistent = bool(
            result.get("ownership_consistent")
        )
        self.pickup_safety_runtime_consistent = bool(
            result.get("runtime_consistent")
        )
        self.pickup_safety_retry_allowed = bool(result.get("retry_allowed"))
        self.pickup_safety_active_claims = max(
            0,
            int(result.get("active_claims") or 0),
        )
        self.pickup_safety_stale_claims = max(
            0,
            int(result.get("stale_claims") or 0),
        )
        self.pickup_safety_orphaned_claims = max(
            0,
            int(result.get("orphaned_claims") or 0),
        )
        self.pickup_safety_foreign_runtime_claims = max(
            0,
            int(result.get("foreign_runtime_claims") or 0),
        )
        self.pickup_safety_invalid_claims = max(
            0,
            int(result.get("invalid_claims") or 0),
        )
        self.pickup_safety_max_concurrent_claims = max(
            0,
            int(result.get("max_concurrent_claims") or 0),
        )
        self.pickup_safety_max_stale_claims = max(
            0,
            int(result.get("max_stale_claims") or 0),
        )
        self.pickup_safety_max_orphaned_claims = max(
            0,
            int(result.get("max_orphaned_claims") or 0),
        )
        self.pickup_safety_max_invalid_claims = max(
            0,
            int(result.get("max_invalid_claims") or 0),
        )
        self.pickup_safety_max_foreign_runtime_claims = max(
            0,
            int(result.get("max_foreign_runtime_claims") or 0),
        )
        self.pickup_safety_retry_attempts = max(
            0,
            int(result.get("pickup_retry_attempts") or 0),
        )
        self.pickup_safety_max_retries = max(
            0,
            int(result.get("max_pickup_retries") or 0),
        )
        self.pickup_safety_retry_window_seconds = max(
            0,
            int(result.get("retry_window_seconds") or 0),
        )
        self.pickup_safety_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.pickup_safety_runner_id = result.get("runner_id")
        self.pickup_safety_runtime_id = result.get("runtime_id")
        self.pickup_safety_last_error = result.get("error")
        if self.pickup_safety_status == "error":
            self.pickup_safety_errors += 1

    def mark_pickup_safety_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_pickup_safety_at = datetime.now(timezone.utc)
        self.pickup_safety_iteration += 1
        self.pickup_safety_last_duration_ms = max(0, int(duration_ms or 0))
        self.pickup_safety_errors += 1
        self.pickup_safety_status = "error"
        self.pickup_safety_allows_pickup = False
        self.pickup_safety_last_error = error or "unknown_pickup_safety_error"

    def mark_task_execution_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_concurrent_executions: int = 0,
        max_duration_seconds: int = 0,
        max_runtime_load: float = 0.0,
        max_memory_mb: int = 0,
        runtime_owner: str | None = None,
    ) -> None:
        self.task_execution_started_at = datetime.now(timezone.utc)
        self.execution_enabled = bool(enabled)
        self.execution_status = "active" if enabled else "disabled"
        self.execution_interval_seconds = interval_seconds
        self.max_concurrent_executions = max(
            0,
            int(max_concurrent_executions or 0),
        )
        self.max_execution_duration_seconds = max(
            0,
            int(max_duration_seconds or 0),
        )
        self.max_runtime_load = max(0.0, float(max_runtime_load or 0.0))
        self.max_execution_memory_mb = max(0, int(max_memory_mb or 0))
        self.execution_runtime_owner = runtime_owner
        self.execution_last_error = None

    def mark_task_execution_result(self, result: dict) -> None:
        self.last_execution_at = datetime.now(timezone.utc)
        self.execution_iteration += 1
        self.execution_status = result.get("status") or "unknown"
        self.execution_last_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.active_executions = max(
            0,
            int(result.get("active_executions") or 0),
        )
        self.max_concurrent_executions = max(
            0,
            int(result.get("max_concurrent_executions") or 0),
        )
        self.max_execution_duration_seconds = max(
            0,
            int(result.get("max_duration_seconds") or 0),
        )
        self.max_runtime_load = max(
            0.0,
            float(result.get("max_runtime_load") or 0.0),
        )
        runtime_load = result.get("runtime_load")
        self.runtime_load = float(runtime_load) if runtime_load is not None else None
        self.max_execution_memory_mb = max(
            0,
            int(result.get("max_memory_mb") or 0),
        )
        memory_usage = result.get("memory_usage_mb")
        self.execution_memory_usage_mb = (
            float(memory_usage) if memory_usage is not None else None
        )
        self.last_execution_id = result.get("execution_id")
        self.last_execution_state = result.get("execution_state")
        self.last_execution_task_id = result.get("task_id")
        self.last_execution_task_title = result.get("task_title")
        self.last_execution_started_at = result.get("started_at")
        self.last_execution_finished_at = result.get("finished_at")
        self.last_execution_duration_ms = max(
            0,
            int(result.get("execution_duration_ms") or 0),
        )
        self.execution_runtime_owner = result.get("runtime_owner")
        self.execution_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.execution_last_error = result.get("error")

        if self.execution_status == "prepared":
            self.executions_prepared += 1
        elif self.execution_status == "started":
            self.executions_started += 1
        elif self.execution_status == "completed":
            self.executions_completed += 1
        elif self.execution_status == "rejected":
            self.executions_rejected += 1
        elif self.execution_status == "error":
            self.execution_errors += 1

    def mark_task_execution_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_execution_at = datetime.now(timezone.utc)
        self.execution_iteration += 1
        self.execution_last_duration_ms = max(0, int(duration_ms or 0))
        self.execution_errors += 1
        self.execution_status = "error"
        self.execution_last_error = error or "unknown_execution_error"

    def mark_execution_session_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_active_sessions: int = 0,
        max_log_entries: int = 0,
        runtime_owner: str | None = None,
    ) -> None:
        self.execution_session_started_at = datetime.now(timezone.utc)
        self.execution_session_enabled = bool(enabled)
        self.execution_session_status = "active" if enabled else "disabled"
        self.execution_session_state = "ready" if enabled else "disabled"
        self.execution_session_interval_seconds = interval_seconds
        self.execution_session_max_active_sessions = max(
            0,
            int(max_active_sessions or 0),
        )
        self.execution_session_max_log_entries = max(
            0,
            int(max_log_entries or 0),
        )
        self.execution_session_runtime_owner = runtime_owner
        self.execution_session_last_error = None

    def mark_execution_session_completed(self, result: dict) -> None:
        self.last_execution_session_at = datetime.now(timezone.utc)
        self.execution_session_iteration += 1
        self.execution_session_status = result.get("status") or "unknown"
        self.execution_session_state = result.get("session_state")
        self.execution_session_last_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.execution_session_runtime_protected = bool(
            result.get("runtime_protected", True)
        )
        self.execution_session_active_sessions = max(
            0,
            int(result.get("active_sessions") or 0),
        )
        self.execution_session_max_active_sessions = max(
            0,
            int(result.get("max_active_sessions") or 0),
        )
        self.execution_session_recovery_available = bool(
            result.get("recovery_available")
        )
        self.execution_session_runtime_owner = result.get("runtime_owner")
        self.last_execution_session_id = result.get("session_id")
        self.last_execution_session_task_id = result.get("task_id")
        self.last_execution_session_phase_id = result.get("phase_id")
        self.last_execution_session_audit_status = result.get("audit_status")
        self.last_execution_session_checkpoint = result.get("last_checkpoint")
        self.last_execution_session_action = result.get("last_action")
        self.last_execution_session_file_modified = result.get(
            "last_file_modified"
        )
        self.last_execution_session_result = result.get("last_result")
        self.last_execution_session_error_detail = result.get("last_error")
        self.last_execution_session_audit = result.get("last_audit")
        self.execution_session_modified_files = [
            str(path) for path in (result.get("modified_files") or [])
        ]
        self.last_execution_session_human_approval_status = result.get(
            "human_approval_status"
        )
        context_snapshot = result.get("context_snapshot")
        self.execution_session_context_snapshot = (
            dict(context_snapshot) if isinstance(context_snapshot, dict) else None
        )
        self.execution_session_context_recovery_available = bool(
            result.get("context_recovery_available")
        )
        self.execution_session_log_count = max(
            0,
            int(result.get("log_count") or 0),
        )
        last_log = result.get("last_log")
        self.execution_session_last_log = (
            dict(last_log) if isinstance(last_log, dict) else None
        )
        self.last_execution_session_previous_state = result.get("previous_state")
        self.last_execution_session_transition = result.get("state_transition")
        self.execution_session_transition_allowed = bool(
            result.get("state_transition_allowed", True)
        )
        self.execution_session_blocking_detected = bool(
            result.get("blocking_detected")
        )
        self.execution_session_blocking_reasons = [
            str(reason) for reason in (result.get("blocking_reasons") or [])
        ]
        self.last_execution_session_lifecycle_stage = result.get(
            "lifecycle_stage"
        )
        self.last_execution_session_lifecycle_transition = result.get(
            "lifecycle_transition"
        )
        self.execution_session_lifecycle_transition_allowed = bool(
            result.get("lifecycle_transition_allowed", True)
        )
        session = result.get("session")
        self.execution_session_snapshot = (
            dict(session) if isinstance(session, dict) else None
        )
        self.execution_session_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.execution_session_last_error = result.get("error")
        if self.execution_session_status == "error":
            self.execution_session_errors += 1

    def mark_execution_session_error(
        self,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        self.last_execution_session_at = datetime.now(timezone.utc)
        self.execution_session_iteration += 1
        self.execution_session_last_duration_ms = max(0, int(duration_ms or 0))
        self.execution_session_errors += 1
        self.execution_session_status = "error"
        self.execution_session_state = "error"
        self.execution_session_runtime_protected = True
        self.execution_session_transition_allowed = False
        self.execution_session_lifecycle_transition_allowed = False
        self.execution_session_blocking_detected = True
        self.execution_session_last_error = (
            error or "unknown_execution_session_error"
        )

    def mark_execution_safety_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_retries: int = 0,
        max_concurrent_executions: int = 0,
        max_duration_seconds: int = 0,
        max_runtime_load: float = 0.0,
        max_memory_mb: int = 0,
        max_concurrent_provider_calls: int = 0,
    ) -> None:
        self.execution_safety_started_at = datetime.now(timezone.utc)
        self.execution_safety_enabled = bool(enabled)
        self.execution_safety_status = "active" if enabled else "disabled"
        self.execution_safety_interval_seconds = interval_seconds
        self.execution_max_retries = max(0, int(max_retries or 0))
        self.execution_safety_max_concurrent_executions = max(
            0,
            int(max_concurrent_executions or 0),
        )
        self.max_execution_duration_seconds = max(
            0,
            int(max_duration_seconds or 0),
        )
        self.execution_safety_max_runtime_load = max(
            0.0,
            float(max_runtime_load or 0.0),
        )
        self.execution_safety_max_memory_mb = max(0, int(max_memory_mb or 0))
        self.execution_safety_max_concurrent_provider_calls = max(
            0,
            int(max_concurrent_provider_calls or 0),
        )
        self.execution_safety_last_error = None

    def mark_execution_safety_completed(self, result: dict) -> None:
        self.last_execution_safety_at = datetime.now(timezone.utc)
        self.execution_safety_iteration += 1
        self.execution_safety_status = result.get("status") or "unknown"
        self.execution_safety_last_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.execution_safety_allows_execution = bool(
            result.get("allows_execution")
        )
        self.execution_safety_runtime_protected = bool(
            result.get("runtime_protected")
        )
        self.execution_conflict_detected = bool(result.get("conflict_detected"))
        self.execution_timeout_detected = bool(result.get("timeout_detected"))
        self.execution_provider_failure_detected = bool(
            result.get("provider_failure_detected")
        )
        self.execution_retry_allowed = bool(result.get("retry_allowed"))
        self.execution_retry_attempts = max(
            0,
            int(result.get("retry_attempts") or 0),
        )
        self.execution_max_retries = max(0, int(result.get("max_retries") or 0))
        self.execution_safety_active_executions = max(
            0,
            int(result.get("active_executions") or 0),
        )
        self.execution_safety_max_concurrent_executions = max(
            0,
            int(result.get("max_concurrent_executions") or 0),
        )
        runtime_load = result.get("runtime_load")
        self.execution_safety_runtime_load = (
            float(runtime_load) if runtime_load is not None else None
        )
        self.execution_safety_max_runtime_load = max(
            0.0,
            float(result.get("max_runtime_load") or 0.0),
        )
        memory_usage = result.get("memory_usage_mb")
        self.execution_safety_memory_usage_mb = (
            float(memory_usage) if memory_usage is not None else None
        )
        self.execution_safety_max_memory_mb = max(
            0,
            int(result.get("max_memory_mb") or 0),
        )
        self.execution_safety_active_provider_calls = max(
            0,
            int(result.get("active_provider_calls") or 0),
        )
        self.execution_safety_max_concurrent_provider_calls = max(
            0,
            int(result.get("max_concurrent_provider_calls") or 0),
        )
        self.execution_safety_provider_status = result.get("provider_status")
        self.execution_safety_execution_status = result.get("execution_status")
        self.execution_safety_execution_id = result.get("execution_id")
        self.execution_safety_task_id = result.get("task_id")
        self.execution_safety_checked_at = result.get("checked_at")
        self.execution_safety_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.execution_safety_last_error = result.get("error")
        if self.execution_safety_status == "error":
            self.execution_safety_errors += 1

    def mark_execution_safety_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_execution_safety_at = datetime.now(timezone.utc)
        self.execution_safety_iteration += 1
        self.execution_safety_last_duration_ms = max(0, int(duration_ms or 0))
        self.execution_safety_errors += 1
        self.execution_safety_status = "error"
        self.execution_safety_allows_execution = False
        self.execution_safety_runtime_protected = True
        self.execution_safety_last_error = error or "unknown_execution_safety_error"

    def mark_timeout_control_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_concurrent_timeout_checks: int = 0,
        max_tracking_duration_ms: int = 0,
        max_runtime_timeout_load: float = 0.0,
        max_timeout_check_duration_ms: int = 0,
    ) -> None:
        self.timeout_control_started_at = datetime.now(timezone.utc)
        self.timeout_control_enabled = bool(enabled)
        self.timeout_control_status = "active" if enabled else "disabled"
        self.timeout_state = "ready" if enabled else "disabled"
        self.timeout_control_interval_seconds = interval_seconds
        self.max_concurrent_timeout_checks = max(
            0,
            int(max_concurrent_timeout_checks or 0),
        )
        self.max_timeout_tracking_duration_ms = max(
            0,
            int(max_tracking_duration_ms or 0),
        )
        self.max_runtime_timeout_load = max(
            0.0,
            float(max_runtime_timeout_load or 0.0),
        )
        self.max_timeout_check_duration_ms = max(
            0,
            int(max_timeout_check_duration_ms or 0),
        )
        self.timeout_control_last_error = None

    def mark_timeout_control_result(self, result: dict) -> None:
        self.last_timeout_control_at = datetime.now(timezone.utc)
        self.timeout_control_iteration += 1
        self.timeout_control_status = result.get("status") or "unknown"
        self.timeout_state = result.get("timeout_state")
        self.timeout_control_last_duration_ms = max(
            0,
            int(result.get("timeout_check_duration_ms") or 0),
        )
        self.timeout_monitoring_allowed = bool(
            result.get("monitoring_allowed")
        )
        self.timeout_runtime_protected = bool(
            result.get("runtime_protected", True)
        )
        self.timeout_detected = bool(result.get("timeout_detected"))
        self.timeout_registered = bool(result.get("timeout_registered"))
        self.timeout_duration_tracking = bool(result.get("duration_tracking"))
        self.timeout_linkage_valid = bool(result.get("linkage_valid", True))
        self.timeout_ownership_consistent = bool(
            result.get("ownership_consistent", True)
        )
        self.active_timeout_checks = max(
            0,
            int(result.get("active_timeout_checks") or 0),
        )
        self.max_concurrent_timeout_checks = max(
            0,
            int(result.get("max_concurrent_timeout_checks") or 0),
        )
        runtime_load = result.get("runtime_timeout_load")
        self.runtime_timeout_load = (
            float(runtime_load) if runtime_load is not None else None
        )
        self.max_runtime_timeout_load = max(
            0.0,
            float(result.get("max_runtime_timeout_load") or 0.0),
        )
        self.max_timeout_tracking_duration_ms = max(
            0,
            int(result.get("max_tracking_duration_ms") or 0),
        )
        self.max_timeout_check_duration_ms = max(
            0,
            int(result.get("max_timeout_check_duration_ms") or 0),
        )
        self.last_timeout_id = result.get("timeout_id")
        self.last_timeout_execution_id = result.get("execution_id")
        self.last_timeout_task_id = result.get("task_id")
        self.last_timeout_runtime_id = result.get("runtime_id")
        self.last_timeout_runtime_owner = result.get("runtime_owner")
        self.last_timeout_execution_state = result.get("execution_state")
        self.last_timeout_execution_started_at = result.get(
            "execution_started_at"
        )
        self.last_timeout_detected_at = result.get("detected_at")
        self.last_timeout_checked_at = result.get("checked_at")
        self.timeout_execution_duration_ms = max(
            0,
            int(result.get("current_runtime_duration_ms") or 0),
        )
        self.timeout_threshold_ms = max(
            0,
            int(result.get("timeout_threshold_ms") or 0),
        )
        self.timeout_control_metadata = dict(result.get("metadata") or {})
        self.timeout_control_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.timeout_control_last_error = result.get("error")

        if self.timeout_control_status in {"clear", "tracking"}:
            self.timeout_checks_passed += 1
        elif self.timeout_control_status == "timeout_detected":
            self.timeouts_detected += 1
        elif self.timeout_control_status == "rejected":
            self.timeout_checks_rejected += 1
        elif self.timeout_control_status == "error":
            self.timeout_checks_failed += 1
            self.timeout_control_errors += 1

    def mark_timeout_control_error(
        self,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        self.last_timeout_control_at = datetime.now(timezone.utc)
        self.timeout_control_iteration += 1
        self.timeout_control_last_duration_ms = max(0, int(duration_ms or 0))
        self.timeout_control_errors += 1
        self.timeout_checks_failed += 1
        self.timeout_control_status = "error"
        self.timeout_state = "error"
        self.timeout_monitoring_allowed = False
        self.timeout_runtime_protected = True
        self.timeout_control_last_error = error or "unknown_timeout_control_error"

    def mark_retry_control_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_retry_attempts: int = 0,
        max_concurrent_retries: int = 0,
        max_retry_duration_ms: int = 0,
        max_runtime_retry_load: float = 0.0,
        max_retry_overhead_ms: int = 0,
    ) -> None:
        self.retry_control_started_at = datetime.now(timezone.utc)
        self.retry_control_enabled = bool(enabled)
        self.retry_control_status = "active" if enabled else "disabled"
        self.retry_state = "ready" if enabled else "disabled"
        self.retry_control_interval_seconds = interval_seconds
        self.max_retry_attempts = max(0, int(max_retry_attempts or 0))
        self.max_concurrent_retries = max(
            0,
            int(max_concurrent_retries or 0),
        )
        self.max_retry_duration_ms = max(0, int(max_retry_duration_ms or 0))
        self.max_runtime_retry_load = max(
            0.0,
            float(max_runtime_retry_load or 0.0),
        )
        self.max_retry_overhead_ms = max(0, int(max_retry_overhead_ms or 0))
        self.retry_control_last_error = None

    def mark_retry_control_result(self, result: dict) -> None:
        self.last_retry_control_at = datetime.now(timezone.utc)
        self.retry_control_iteration += 1
        self.retry_control_status = result.get("status") or "unknown"
        self.retry_state = result.get("retry_state")
        self.retry_control_last_duration_ms = max(
            0,
            int(result.get("retry_control_overhead_ms") or 0),
        )
        self.retry_allowed = bool(result.get("retry_allowed"))
        self.retry_runtime_protected = bool(result.get("runtime_protected", True))
        self.retry_linkage_valid = bool(result.get("linkage_valid", True))
        self.retry_ownership_consistent = bool(
            result.get("ownership_consistent", True)
        )
        self.retry_threshold_valid = bool(result.get("threshold_valid", True))
        self.retry_provider_available = bool(result.get("provider_available", True))
        self.active_retries = max(0, int(result.get("active_retries") or 0))
        self.max_concurrent_retries = max(
            0,
            int(result.get("max_concurrent_retries") or 0),
        )
        runtime_load = result.get("runtime_retry_load")
        self.runtime_retry_load = (
            float(runtime_load) if runtime_load is not None else None
        )
        self.max_runtime_retry_load = max(
            0.0,
            float(result.get("max_runtime_retry_load") or 0.0),
        )
        self.max_retry_duration_ms = max(
            0,
            int(result.get("max_retry_duration_ms") or 0),
        )
        self.max_retry_overhead_ms = max(
            0,
            int(result.get("max_retry_overhead_ms") or 0),
        )
        self.last_retry_id = result.get("retry_id")
        self.last_retry_execution_id = result.get("execution_id")
        self.last_retry_task_id = result.get("task_id")
        self.last_retry_runner_id = result.get("runner_id")
        self.last_retry_runtime_id = result.get("runtime_id")
        self.last_retry_runtime_owner = result.get("runtime_owner")
        self.last_retry_execution_state = result.get("execution_state")
        self.last_retry_task_status = result.get("task_status")
        self.last_retry_provider_status = result.get("provider_status")
        self.last_retry_attempt = max(0, int(result.get("retry_attempt") or 0))
        self.last_retry_threshold = max(
            0,
            int(result.get("retry_threshold") or 0),
        )
        self.last_retry_reason = result.get("retry_reason")
        self.last_retry_started_at = result.get("retry_started_at")
        self.last_retry_completed_at = result.get("retry_completed_at")
        self.last_retry_duration_ms = max(
            0,
            int(result.get("retry_duration_ms") or 0),
        )
        self.retry_control_metadata = dict(result.get("metadata") or {})
        self.retry_control_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.retry_control_last_error = result.get("error")

        if self.retry_control_status == "registered":
            self.retries_registered += 1
        elif self.retry_control_status == "executing":
            self.retries_started += 1
        elif self.retry_control_status == "completed":
            self.retries_completed += 1
        elif self.retry_control_status == "rejected":
            self.retries_rejected += 1
        elif self.retry_control_status == "failed":
            self.retries_failed += 1
        elif self.retry_control_status == "error":
            self.retries_failed += 1
            self.retry_control_errors += 1

    def mark_retry_control_error(
        self,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        self.last_retry_control_at = datetime.now(timezone.utc)
        self.retry_control_iteration += 1
        self.retry_control_last_duration_ms = max(0, int(duration_ms or 0))
        self.retry_control_errors += 1
        self.retries_failed += 1
        self.retry_control_status = "error"
        self.retry_state = "error"
        self.retry_allowed = False
        self.retry_runtime_protected = True
        self.retry_control_last_error = error or "unknown_retry_control_error"

    def mark_orchestration_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_active_orchestrations: int = 0,
        max_execution_dependencies: int = 0,
        max_dependency_chain: int = 0,
        max_orchestration_duration_ms: int = 0,
        max_orchestration_load: float = 0.0,
        max_coordination_overhead_ms: int = 0,
    ) -> None:
        self.orchestration_started_at = datetime.now(timezone.utc)
        self.orchestration_enabled = bool(enabled)
        self.orchestration_status = "active" if enabled else "disabled"
        self.orchestration_state = "ready" if enabled else "disabled"
        self.dependency_state = "clear" if enabled else "disabled"
        self.orchestration_interval_seconds = interval_seconds
        self.max_active_orchestrations = max(
            0,
            int(max_active_orchestrations or 0),
        )
        self.max_execution_dependencies = max(
            0,
            int(max_execution_dependencies or 0),
        )
        self.max_dependency_chain = max(0, int(max_dependency_chain or 0))
        self.max_orchestration_duration_ms = max(
            0,
            int(max_orchestration_duration_ms or 0),
        )
        self.max_orchestration_load = max(
            0.0,
            float(max_orchestration_load or 0.0),
        )
        self.max_coordination_overhead_ms = max(
            0,
            int(max_coordination_overhead_ms or 0),
        )
        self.orchestration_last_error = None

    def mark_orchestration_result(self, result: dict) -> None:
        self.last_orchestration_at = datetime.now(timezone.utc)
        self.orchestration_iteration += 1
        self.orchestration_status = result.get("status") or "unknown"
        self.orchestration_state = (
            result.get("orchestration_state")
            or result.get("coordination_state")
        )
        self.dependency_state = (
            result.get("dependency_state")
            or result.get("dependency_status")
        )
        self.orchestration_last_duration_ms = max(
            0,
            int(result.get("coordination_overhead_ms") or 0),
        )
        self.coordination_allowed = bool(result.get("coordination_allowed"))
        self.orchestration_runtime_protected = bool(
            result.get("runtime_protected", True)
        )
        self.orchestration_conflict_detected = bool(
            result.get("conflict_detected")
        )
        self.orchestration_linkage_valid = bool(
            result.get("linkage_valid", True)
        )
        self.orchestration_ownership_consistent = bool(
            result.get("ownership_consistent", True)
        )
        self.orchestration_dependency_valid = bool(
            result.get("dependency_valid", True)
        )
        self.active_orchestrations = max(
            0,
            int(result.get("active_orchestrations") or 0),
        )
        self.max_active_orchestrations = max(
            0,
            int(result.get("max_active_orchestrations") or 0),
        )
        runtime_load = result.get("runtime_orchestration_load")
        self.runtime_orchestration_load = (
            float(runtime_load) if runtime_load is not None else None
        )
        self.max_orchestration_load = max(
            0.0,
            float(result.get("max_orchestration_load") or 0.0),
        )
        self.max_execution_dependencies = max(
            0,
            int(result.get("max_execution_dependencies") or 0),
        )
        self.max_dependency_chain = max(
            0,
            int(result.get("max_dependency_chain") or 0),
        )
        self.max_orchestration_duration_ms = max(
            0,
            int(result.get("max_orchestration_duration_ms") or 0),
        )
        self.max_coordination_overhead_ms = max(
            0,
            int(result.get("max_coordination_overhead_ms") or 0),
        )
        self.last_orchestration_id = (
            result.get("coordination_id") or result.get("orchestration_id")
        )
        self.last_orchestration_execution_id = result.get("execution_id")
        self.last_orchestration_task_id = result.get("task_id")
        self.last_orchestration_runner_id = result.get("runner_id")
        self.last_orchestration_runtime_id = result.get("runtime_id")
        self.last_orchestration_runtime_owner = result.get("runtime_owner")
        self.last_orchestration_execution_state = result.get("execution_state")
        self.last_orchestration_task_status = result.get("task_status")
        self.last_orchestration_execution_order = max(
            0,
            int(
                result.get("execution_sequence")
                or result.get("execution_order")
                or 0
            ),
        )
        self.last_orchestration_dependency_count = max(
            0,
            int(result.get("dependency_count") or 0),
        )
        self.last_coordination_started_at = result.get("coordination_started_at")
        self.last_coordination_completed_at = result.get(
            "coordination_completed_at"
        )
        self.last_coordination_duration_ms = max(
            0,
            int(result.get("coordination_duration_ms") or 0),
        )
        self.orchestration_dependencies = [
            dict(item) for item in (result.get("dependencies") or [])
        ]
        self.orchestration_metadata = dict(result.get("metadata") or {})
        self.orchestration_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.orchestration_last_error = result.get("error")

        if self.orchestration_status == "registered":
            self.orchestrations_registered += 1
        elif self.orchestration_status == "coordinating":
            self.orchestrations_started += 1
        elif self.orchestration_status == "released":
            self.orchestrations_completed += 1
            self.orchestrations_released += 1
        elif self.orchestration_status == "rejected":
            self.orchestrations_rejected += 1
        elif self.orchestration_status == "failed":
            self.orchestrations_failed += 1
        elif self.orchestration_status == "error":
            self.orchestrations_failed += 1
            self.orchestration_errors += 1

    def mark_orchestration_error(
        self,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        self.last_orchestration_at = datetime.now(timezone.utc)
        self.orchestration_iteration += 1
        self.orchestration_last_duration_ms = max(0, int(duration_ms or 0))
        self.orchestration_errors += 1
        self.orchestrations_failed += 1
        self.orchestration_status = "error"
        self.orchestration_state = "error"
        self.dependency_state = "unknown"
        self.coordination_allowed = False
        self.orchestration_runtime_protected = True
        self.orchestration_last_error = error or "unknown_orchestration_error"

    def mark_orchestration_safety_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_retries: int = 0,
        max_orchestration_duration_ms: int = 0,
        max_coordination_overhead_ms: int = 0,
    ) -> None:
        self.orchestration_safety_started_at = datetime.now(timezone.utc)
        self.orchestration_safety_enabled = bool(enabled)
        self.orchestration_safety_status = "active" if enabled else "disabled"
        self.orchestration_safety_state = "ready" if enabled else "disabled"
        self.orchestration_safety_interval_seconds = interval_seconds
        self.orchestration_safety_max_retries = max(0, int(max_retries or 0))
        self.orchestration_safety_max_duration_ms = max(
            0,
            int(max_orchestration_duration_ms or 0),
        )
        self.orchestration_safety_max_overhead_ms = max(
            0,
            int(max_coordination_overhead_ms or 0),
        )
        self.orchestration_safety_last_error = None

    def mark_orchestration_safety_completed(self, result: dict) -> None:
        self.last_orchestration_safety_at = datetime.now(timezone.utc)
        self.orchestration_safety_iteration += 1
        self.orchestration_safety_status = result.get("status") or "unknown"
        self.orchestration_safety_state = result.get("safety_state")
        self.orchestration_safety_last_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.orchestration_safety_allows_orchestration = bool(
            result.get("allows_orchestration")
        )
        self.orchestration_safety_runtime_protected = bool(
            result.get("runtime_protected", True)
        )
        self.orchestration_safety_conflict_detected = bool(
            result.get("conflict_detected")
        )
        self.orchestration_safety_dependency_corruption_detected = bool(
            result.get("dependency_corruption_detected")
        )
        self.orchestration_safety_sequencing_violation_detected = bool(
            result.get("sequencing_violation_detected")
        )
        self.orchestration_safety_runaway_detected = bool(
            result.get("runaway_detected")
        )
        self.orchestration_safety_timeout_detected = bool(
            result.get("timeout_detected")
        )
        self.orchestration_safety_retry_allowed = bool(
            result.get("retry_allowed")
        )
        self.orchestration_safety_retry_attempts = max(
            0,
            int(result.get("retry_attempts") or 0),
        )
        self.orchestration_safety_max_retries = max(
            0,
            int(result.get("max_retries") or 0),
        )
        self.orchestration_safety_active_orchestrations = max(
            0,
            int(result.get("active_orchestrations") or 0),
        )
        self.orchestration_safety_max_active_orchestrations = max(
            0,
            int(result.get("max_active_orchestrations") or 0),
        )
        runtime_load = result.get("runtime_orchestration_load")
        self.orchestration_safety_runtime_load = (
            float(runtime_load) if runtime_load is not None else None
        )
        self.orchestration_safety_max_runtime_load = max(
            0.0,
            float(result.get("max_orchestration_load") or 0.0),
        )
        self.orchestration_safety_coordination_duration_ms = max(
            0,
            int(result.get("coordination_duration_ms") or 0),
        )
        self.orchestration_safety_max_duration_ms = max(
            0,
            int(result.get("max_orchestration_duration_ms") or 0),
        )
        self.orchestration_safety_coordination_overhead_ms = max(
            0,
            int(result.get("coordination_overhead_ms") or 0),
        )
        self.orchestration_safety_max_overhead_ms = max(
            0,
            int(result.get("max_coordination_overhead_ms") or 0),
        )
        self.last_orchestration_safety_id = result.get("safety_id")
        self.orchestration_safety_coordination_id = (
            result.get("coordination_id") or result.get("orchestration_id")
        )
        self.orchestration_safety_execution_id = result.get("execution_id")
        self.orchestration_safety_task_id = result.get("task_id")
        self.orchestration_safety_runtime_owner = result.get("runtime_owner")
        self.orchestration_safety_dependencies = [
            dict(item) for item in (result.get("dependencies") or [])
        ]
        self.orchestration_safety_metadata = dict(result.get("metadata") or {})
        self.orchestration_safety_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.orchestration_safety_last_error = result.get("error")
        if self.orchestration_safety_status == "error":
            self.orchestration_safety_errors += 1

    def mark_orchestration_safety_error(
        self,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        self.last_orchestration_safety_at = datetime.now(timezone.utc)
        self.orchestration_safety_iteration += 1
        self.orchestration_safety_last_duration_ms = max(
            0,
            int(duration_ms or 0),
        )
        self.orchestration_safety_errors += 1
        self.orchestration_safety_status = "error"
        self.orchestration_safety_state = "error"
        self.orchestration_safety_allows_orchestration = False
        self.orchestration_safety_runtime_protected = True
        self.orchestration_safety_last_error = (
            error or "unknown_orchestration_safety_error"
        )

    def mark_provider_bridge_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_concurrent_calls: int = 0,
        max_requests_per_minute: int = 0,
        max_request_bytes: int = 0,
        timeout_seconds: float = 0.0,
        max_response_bytes: int = 0,
    ) -> None:
        self.provider_bridge_started_at = datetime.now(timezone.utc)
        self.provider_bridge_enabled = bool(enabled)
        self.provider_bridge_status = "active" if enabled else "disabled"
        self.provider_bridge_interval_seconds = interval_seconds
        self.max_concurrent_provider_calls = max(0, int(max_concurrent_calls or 0))
        self.max_provider_requests_per_minute = max(
            0,
            int(max_requests_per_minute or 0),
        )
        self.max_provider_request_bytes = max(0, int(max_request_bytes or 0))
        self.provider_timeout_seconds = max(0.0, float(timeout_seconds or 0.0))
        self.max_provider_response_bytes = max(0, int(max_response_bytes or 0))
        self.active_provider_sessions = 0
        self.provider_connection_status = "idle" if enabled else "disabled"
        self.provider_failure_status = None
        self.provider_connection_states = []
        self.provider_bridge_last_error = None

    def mark_provider_bridge_result(self, result: dict) -> None:
        self.last_provider_bridge_at = datetime.now(timezone.utc)
        self.provider_bridge_iteration += 1
        self.provider_bridge_status = result.get("status") or "unknown"
        self.provider_bridge_last_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.active_provider_calls = max(
            0,
            int(result.get("active_provider_calls") or 0),
        )
        self.active_provider_sessions = max(
            0,
            int(result.get("active_provider_sessions") or 0),
        )
        self.max_concurrent_provider_calls = max(
            0,
            int(result.get("max_concurrent_provider_calls") or 0),
        )
        self.max_provider_requests_per_minute = max(
            0,
            int(result.get("max_requests_per_minute") or 0),
        )
        self.provider_requests_in_window = max(
            0,
            int(result.get("requests_in_window") or 0),
        )
        self.max_provider_request_bytes = max(
            0,
            int(result.get("max_request_bytes") or 0),
        )
        self.provider_request_size_bytes = max(
            0,
            int(result.get("request_size_bytes") or 0),
        )
        self.provider_timeout_seconds = max(
            0.0,
            float(result.get("timeout_seconds") or 0.0),
        )
        self.max_provider_response_bytes = max(
            0,
            int(result.get("max_response_bytes") or 0),
        )
        self.provider_response_size_bytes = max(
            0,
            int(result.get("response_size_bytes") or 0),
        )
        self.provider_name = result.get("provider_name")
        self.provider_session_id = result.get("provider_session_id")
        self.provider_connection_status = result.get("connection_status")
        self.provider_failure_status = result.get("failure_status")
        self.provider_connection_states = [
            str(state) for state in (result.get("connection_states") or [])
        ]
        self.provider_model = result.get("model")
        self.provider_request_id = result.get("request_id")
        self.provider_execution_id = result.get("execution_id")
        self.provider_task_id = result.get("task_id")
        self.provider_started_at = result.get("started_at")
        self.provider_finished_at = result.get("finished_at")
        self.provider_duration_ms = max(
            0,
            int(result.get("provider_duration_ms") or 0),
        )
        self.provider_usage = dict(result.get("usage") or {})
        self.provider_input_tokens = max(
            0,
            int(self.provider_usage.get("input_tokens") or 0),
        )
        self.provider_output_tokens = max(
            0,
            int(self.provider_usage.get("output_tokens") or 0),
        )
        self.provider_total_tokens = (
            self.provider_input_tokens + self.provider_output_tokens
        )
        self.provider_bridge_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.provider_bridge_last_error = result.get("error")

        if self.provider_bridge_status == "completed":
            self.provider_requests_completed += 1
        elif self.provider_bridge_status == "rejected":
            self.provider_requests_rejected += 1
        elif self.provider_bridge_status == "timeout":
            self.provider_timeouts += 1
            self.provider_requests_failed += 1
        elif self.provider_bridge_status == "invalid_response":
            self.provider_invalid_responses += 1
            self.provider_requests_failed += 1
        elif self.provider_bridge_status in {"error", "provider_error"}:
            self.provider_requests_failed += 1
            self.provider_bridge_errors += 1

    def mark_provider_bridge_error(self, error: str, duration_ms: int = 0) -> None:
        self.last_provider_bridge_at = datetime.now(timezone.utc)
        self.provider_bridge_iteration += 1
        self.provider_bridge_last_duration_ms = max(0, int(duration_ms or 0))
        self.provider_bridge_errors += 1
        self.provider_bridge_status = "error"
        self.provider_connection_status = "failed"
        self.provider_failure_status = error or "unknown_provider_bridge_error"
        self.provider_bridge_last_error = error or "unknown_provider_bridge_error"

    def mark_response_ingestion_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_concurrent_ingestions: int = 0,
        max_response_bytes: int = 0,
        max_ingestion_duration_ms: int = 0,
        max_runtime_ingestion_load: float = 0.0,
    ) -> None:
        self.response_ingestion_started_at = datetime.now(timezone.utc)
        self.response_ingestion_enabled = bool(enabled)
        self.response_ingestion_status = "active" if enabled else "disabled"
        self.response_ingestion_state = "ready" if enabled else "disabled"
        self.response_ingestion_interval_seconds = interval_seconds
        self.max_concurrent_response_ingestions = max(
            0,
            int(max_concurrent_ingestions or 0),
        )
        self.max_response_ingestion_bytes = max(0, int(max_response_bytes or 0))
        self.max_response_ingestion_duration_ms = max(
            0,
            int(max_ingestion_duration_ms or 0),
        )
        self.max_response_ingestion_runtime_load = max(
            0.0,
            float(max_runtime_ingestion_load or 0.0),
        )
        self.response_ingestion_last_error = None

    def mark_response_ingestion_result(self, result: dict) -> None:
        self.last_response_ingestion_at = datetime.now(timezone.utc)
        self.response_ingestion_iteration += 1
        self.response_ingestion_status = result.get("status") or "unknown"
        self.response_ingestion_state = result.get("ingestion_state")
        self.response_ingestion_last_duration_ms = max(
            0,
            int(result.get("ingestion_duration_ms") or result.get("duration_ms") or 0),
        )
        self.active_response_ingestions = max(
            0,
            int(result.get("active_ingestions") or 0),
        )
        self.max_concurrent_response_ingestions = max(
            0,
            int(result.get("max_concurrent_ingestions") or 0),
        )
        self.max_response_ingestion_bytes = max(
            0,
            int(result.get("max_response_bytes") or 0),
        )
        self.response_ingestion_size_bytes = max(
            0,
            int(result.get("response_size_bytes") or 0),
        )
        self.max_response_ingestion_duration_ms = max(
            0,
            int(result.get("max_ingestion_duration_ms") or 0),
        )
        runtime_load = result.get("runtime_ingestion_load")
        self.response_ingestion_runtime_load = (
            float(runtime_load) if runtime_load is not None else None
        )
        self.max_response_ingestion_runtime_load = max(
            0.0,
            float(result.get("max_runtime_ingestion_load") or 0.0),
        )
        self.last_response_id = result.get("response_id")
        self.last_response_execution_id = result.get("execution_id")
        self.last_response_task_id = result.get("task_id")
        self.last_response_runtime_id = result.get("runtime_id")
        self.last_response_execution_owner = result.get("execution_owner")
        self.last_response_provider_source = result.get("provider_source")
        self.last_response_provider_request_id = result.get("provider_request_id")
        self.last_response_model = result.get("model")
        self.last_response_received_at = result.get("received_at")
        self.last_response_started_at = result.get("started_at")
        self.last_response_finished_at = result.get("finished_at")
        self.response_storage_prepared = bool(result.get("storage_prepared"))
        self.response_ingestion_metadata = dict(result.get("metadata") or {})
        self.response_ingestion_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.response_ingestion_last_error = result.get("error")

        if self.response_ingestion_status == "ingested":
            self.responses_received += 1
            self.responses_ingested += 1
        elif self.response_ingestion_status == "rejected":
            self.responses_rejected += 1
        elif self.response_ingestion_status == "error":
            self.responses_failed += 1
            self.response_ingestion_errors += 1

    def mark_response_ingestion_error(
        self,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        self.last_response_ingestion_at = datetime.now(timezone.utc)
        self.response_ingestion_iteration += 1
        self.response_ingestion_last_duration_ms = max(0, int(duration_ms or 0))
        self.response_ingestion_errors += 1
        self.responses_failed += 1
        self.response_ingestion_status = "error"
        self.response_ingestion_state = "error"
        self.response_ingestion_last_error = (
            error or "unknown_response_ingestion_error"
        )

    def mark_response_validation_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_concurrent_validations: int = 0,
        max_payload_inspection_bytes: int = 0,
        max_validation_duration_ms: int = 0,
        max_runtime_validation_load: float = 0.0,
    ) -> None:
        self.response_validation_started_at = datetime.now(timezone.utc)
        self.response_validation_enabled = bool(enabled)
        self.response_validation_status = "active" if enabled else "disabled"
        self.response_validation_state = "ready" if enabled else "disabled"
        self.response_validation_interval_seconds = interval_seconds
        self.max_concurrent_response_validations = max(
            0,
            int(max_concurrent_validations or 0),
        )
        self.max_response_validation_payload_bytes = max(
            0,
            int(max_payload_inspection_bytes or 0),
        )
        self.max_response_validation_duration_ms = max(
            0,
            int(max_validation_duration_ms or 0),
        )
        self.max_response_validation_runtime_load = max(
            0.0,
            float(max_runtime_validation_load or 0.0),
        )
        self.response_validation_last_error = None

    def mark_response_validation_result(self, result: dict) -> None:
        self.last_response_validation_at = datetime.now(timezone.utc)
        self.response_validation_iteration += 1
        self.response_validation_status = result.get("status") or "unknown"
        self.response_validation_state = result.get("validation_state")
        self.response_validation_last_duration_ms = max(
            0,
            int(result.get("validation_duration_ms") or result.get("duration_ms") or 0),
        )
        self.active_response_validations = max(
            0,
            int(result.get("active_validations") or 0),
        )
        self.max_concurrent_response_validations = max(
            0,
            int(result.get("max_concurrent_validations") or 0),
        )
        self.max_response_validation_payload_bytes = max(
            0,
            int(result.get("max_payload_inspection_bytes") or 0),
        )
        self.response_validation_payload_size_bytes = max(
            0,
            int(result.get("payload_size_bytes") or 0),
        )
        self.max_response_validation_duration_ms = max(
            0,
            int(result.get("max_validation_duration_ms") or 0),
        )
        runtime_load = result.get("runtime_validation_load")
        self.response_validation_runtime_load = (
            float(runtime_load) if runtime_load is not None else None
        )
        self.max_response_validation_runtime_load = max(
            0.0,
            float(result.get("max_runtime_validation_load") or 0.0),
        )
        self.last_validation_id = result.get("validation_id")
        self.last_validation_execution_id = result.get("execution_id")
        self.last_validation_task_id = result.get("task_id")
        self.last_validation_runtime_id = result.get("runtime_id")
        self.last_validation_execution_owner = result.get("execution_owner")
        self.last_validation_provider_source = result.get("provider_source")
        self.last_validation_provider_request_id = result.get("provider_request_id")
        self.last_validation_model = result.get("model")
        self.last_validation_validated_at = result.get("validated_at")
        self.last_validation_started_at = result.get("started_at")
        self.last_validation_finished_at = result.get("finished_at")
        self.response_validation_metadata = dict(result.get("metadata") or {})
        self.response_validation_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.response_validation_last_error = result.get("error")

        if self.response_validation_status == "validated":
            self.responses_validated += 1
        elif self.response_validation_status == "rejected":
            self.responses_validation_rejected += 1
        elif self.response_validation_status == "error":
            self.responses_validation_failed += 1
            self.response_validation_errors += 1

    def mark_response_validation_error(
        self,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        self.last_response_validation_at = datetime.now(timezone.utc)
        self.response_validation_iteration += 1
        self.response_validation_last_duration_ms = max(0, int(duration_ms or 0))
        self.response_validation_errors += 1
        self.responses_validation_failed += 1
        self.response_validation_status = "error"
        self.response_validation_state = "error"
        self.response_validation_last_error = (
            error or "unknown_response_validation_error"
        )

    def mark_response_safety_started(
        self,
        enabled: bool,
        interval_seconds: float,
        max_concurrent_safety_checks: int = 0,
        max_payload_bytes: int = 0,
        max_safety_duration_ms: int = 0,
        max_runtime_safety_load: float = 0.0,
        max_validation_retries: int = 0,
    ) -> None:
        self.response_safety_started_at = datetime.now(timezone.utc)
        self.response_safety_enabled = bool(enabled)
        self.response_safety_status = "active" if enabled else "disabled"
        self.response_safety_state = "ready" if enabled else "disabled"
        self.response_safety_interval_seconds = interval_seconds
        self.max_concurrent_response_safety_checks = max(
            0,
            int(max_concurrent_safety_checks or 0),
        )
        self.max_response_safety_payload_bytes = max(0, int(max_payload_bytes or 0))
        self.max_response_safety_duration_ms = max(
            0,
            int(max_safety_duration_ms or 0),
        )
        self.max_response_safety_runtime_load = max(
            0.0,
            float(max_runtime_safety_load or 0.0),
        )
        self.response_safety_max_validation_retries = max(
            0,
            int(max_validation_retries or 0),
        )
        self.response_safety_last_error = None

    def mark_response_safety_result(self, result: dict) -> None:
        self.last_response_safety_at = datetime.now(timezone.utc)
        self.response_safety_iteration += 1
        self.response_safety_status = result.get("status") or "unknown"
        self.response_safety_state = result.get("safety_state")
        self.response_safety_last_duration_ms = max(
            0,
            int(result.get("safety_duration_ms") or result.get("duration_ms") or 0),
        )
        self.response_safety_allows_response = bool(result.get("allows_response"))
        self.response_safety_runtime_protected = bool(
            result.get("runtime_protected", True)
        )
        self.response_safety_corrupted_detected = bool(
            result.get("corrupted_detected")
        )
        self.response_safety_poisoning_detected = bool(
            result.get("poisoning_detected")
        )
        self.response_safety_timeout_detected = bool(result.get("timeout_detected"))
        self.response_safety_provider_failure_detected = bool(
            result.get("provider_failure_detected")
        )
        self.response_safety_retry_allowed = bool(result.get("retry_allowed", True))
        self.response_safety_retry_attempts = max(
            0,
            int(result.get("retry_attempts") or 0),
        )
        self.response_safety_max_validation_retries = max(
            0,
            int(result.get("max_validation_retries") or 0),
        )
        self.active_response_safety_checks = max(
            0,
            int(result.get("active_safety_checks") or 0),
        )
        self.max_concurrent_response_safety_checks = max(
            0,
            int(result.get("max_concurrent_safety_checks") or 0),
        )
        self.max_response_safety_payload_bytes = max(
            0,
            int(result.get("max_payload_bytes") or 0),
        )
        self.response_safety_payload_size_bytes = max(
            0,
            int(result.get("payload_size_bytes") or 0),
        )
        self.max_response_safety_duration_ms = max(
            0,
            int(result.get("max_safety_duration_ms") or 0),
        )
        runtime_load = result.get("runtime_safety_load")
        self.response_safety_runtime_load = (
            float(runtime_load) if runtime_load is not None else None
        )
        self.max_response_safety_runtime_load = max(
            0.0,
            float(result.get("max_runtime_safety_load") or 0.0),
        )
        self.last_safety_id = result.get("safety_id")
        self.last_safety_execution_id = result.get("execution_id")
        self.last_safety_task_id = result.get("task_id")
        self.last_safety_runtime_id = result.get("runtime_id")
        self.last_safety_execution_owner = result.get("execution_owner")
        self.last_safety_provider_source = result.get("provider_source")
        self.last_safety_provider_request_id = result.get("provider_request_id")
        self.last_safety_model = result.get("model")
        self.last_safety_checked_at = result.get("checked_at")
        self.last_safety_started_at = result.get("started_at")
        self.last_safety_finished_at = result.get("finished_at")
        self.response_safety_metadata = dict(result.get("metadata") or {})
        self.response_safety_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.response_safety_last_error = result.get("error")

        if self.response_safety_status == "safe":
            self.responses_safety_passed += 1
        elif self.response_safety_status == "blocked":
            self.responses_safety_blocked += 1
        elif self.response_safety_status == "error":
            self.responses_safety_failed += 1
            self.response_safety_errors += 1

    def mark_response_safety_error(
        self,
        error: str,
        duration_ms: int = 0,
    ) -> None:
        self.last_response_safety_at = datetime.now(timezone.utc)
        self.response_safety_iteration += 1
        self.response_safety_last_duration_ms = max(0, int(duration_ms or 0))
        self.response_safety_errors += 1
        self.responses_safety_failed += 1
        self.response_safety_status = "error"
        self.response_safety_state = "error"
        self.response_safety_allows_response = False
        self.response_safety_runtime_protected = True
        self.response_safety_last_error = error or "unknown_response_safety_error"

    def ai_metrics(self) -> dict:
        avg_duration = 0
        avg_provider = 0
        avg_context = 0
        if self.total_ai_requests:
            avg_duration = int(self.total_ai_duration_ms / self.total_ai_requests)
            avg_provider = int(self.total_ai_provider_duration_ms / self.total_ai_requests)
            avg_context = int(self.total_ai_context_build_ms / self.total_ai_requests)

        return {
            "ai_requests_total": self.total_ai_requests,
            "ai_requests_success": self.ai_success_requests,
            "ai_requests_failed": self.ai_failed_requests,
            "ai_avg_duration_ms": avg_duration,
            "last_ai_error": self.last_ai_error,
            "last_ai_request_at": self.last_ai_request_at.isoformat()
            if self.last_ai_request_at
            else None,
            "last_provider": self.last_ai_provider,
            "last_model": self.last_ai_model,
            "total_ai_requests": self.total_ai_requests,
            "ai_success_requests": self.ai_success_requests,
            "ai_failed_requests": self.ai_failed_requests,
            "avg_ai_duration_ms": avg_duration,
            "avg_ai_provider_duration_ms": avg_provider,
            "avg_ai_context_build_ms": avg_context,
            "last_ai_provider": self.last_ai_provider,
            "last_ai_model": self.last_ai_model,
        }

    def telegram_metrics(self) -> dict:
        return {
            "telegram_messages_total": self.telegram_messages_total,
            "telegram_messages_failed": self.telegram_messages_failed,
            "telegram_last_message_at": self.telegram_last_message_at.isoformat()
            if self.telegram_last_message_at
            else None,
            "telegram_last_error": self.telegram_last_error,
            "telegram_messages_processed": self.telegram_messages_processed,
        }

    def health_status(self) -> str:
        if not self.runner_alive:
            return "offline"
        if self.last_loop_at is None:
            return "starting"
        age = (datetime.now(timezone.utc) - self.last_loop_at).total_seconds()
        if age > 30:
            return "degraded"
        return "healthy"

    def runtime_loop_health_status(self) -> str:
        if not self.runtime_loop_alive:
            return "stopped"
        if not self.runtime_safe:
            return "failed"
        if self.degraded_state:
            return "degraded"
        if self.runtime_loop_state == "paused":
            return "paused"
        if self.runtime_loop_last_heartbeat_at is None:
            return "starting"
        max_age = max(30.0, self.runtime_loop_interval_seconds * 3)
        age = (
            datetime.now(timezone.utc) - self.runtime_loop_last_heartbeat_at
        ).total_seconds()
        if age > max_age:
            return "degraded"
        return "healthy"

    def runtime_loop_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "alive": self.runtime_loop_alive,
            "status": self.runtime_loop_health_status(),
            "state": self.runtime_loop_state,
            "started_at": fmt(self.runtime_loop_started_at),
            "last_heartbeat_at": fmt(self.runtime_loop_last_heartbeat_at),
            "last_cycle_duration_ms": self.runtime_loop_last_cycle_duration_ms,
            "iteration": self.runtime_loop_iteration,
            "interval_seconds": self.runtime_loop_interval_seconds,
            "stop_requested": self.runtime_loop_stop_requested,
            "stop_reason": self.runtime_loop_stop_reason,
        }

    def safety_metrics(self) -> dict:
        return {
            "runtime_safe": self.runtime_safe,
            "consecutive_errors": self.consecutive_errors,
            "degraded_state": self.degraded_state,
            "stop_reason": self.safety_stop_reason,
            "safety_events": list(self.safety_events),
        }

    def polling_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.polling_started_at),
            "last_poll_time": fmt(self.last_poll_time),
            "polling_iteration": self.polling_iteration,
            "tasks_detected": self.tasks_detected,
            "polling_status": self.polling_status,
            "polling_interval_seconds": self.polling_interval_seconds,
            "polling_last_duration_ms": self.polling_last_duration_ms,
            "polling_errors": self.polling_errors,
            "polling_last_error": self.polling_last_error,
        }

    def discovery_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.discovery_started_at),
            "last_discovery_at": fmt(self.last_discovery_at),
            "discovery_iteration": self.discovery_iteration,
            "discovery_status": self.discovery_status,
            "discovered_tasks": self.discovered_tasks,
            "discovery_interval_seconds": self.discovery_interval_seconds,
            "discovery_last_duration_ms": self.discovery_last_duration_ms,
            "discovery_errors": self.discovery_errors,
            "discovery_last_error": self.discovery_last_error,
            "discovery_limit": self.discovery_limit,
            "discovery_max_payload_bytes": self.discovery_max_payload_bytes,
            "discovery_query_timeout_seconds": self.discovery_query_timeout_seconds,
            "discovery_ignored_count": self.discovery_ignored_count,
            "discovery_ignored_reasons": dict(self.discovery_ignored_reasons),
            "discovery_filters": dict(self.discovery_filters),
            "discovery_ordering": list(self.discovery_ordering),
            "discovery_candidates": list(self.discovery_candidates),
        }

    def claiming_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.claiming_started_at),
            "last_claiming_at": fmt(self.last_claiming_at),
            "claiming_iteration": self.claiming_iteration,
            "claiming_enabled": self.claiming_enabled,
            "claiming_status": self.claiming_status,
            "claiming_interval_seconds": self.claiming_interval_seconds,
            "claiming_last_duration_ms": self.claiming_last_duration_ms,
            "claiming_errors": self.claiming_errors,
            "claiming_last_error": self.claiming_last_error,
            "claims_attempted": self.claims_attempted,
            "claims_succeeded": self.claims_succeeded,
            "claims_conflicted": self.claims_conflicted,
            "claims_rejected": self.claims_rejected,
            "active_claims": self.active_claims,
            "stale_claims": self.stale_claims,
            "max_concurrent_claims": self.max_concurrent_claims,
            "max_attempts_per_cycle": self.max_attempts_per_cycle,
            "max_task_attempts": self.max_task_attempts,
            "min_claim_interval_seconds": self.min_claim_interval_seconds,
            "stale_claim_after_seconds": self.stale_claim_after_seconds,
            "max_stale_claims": self.max_stale_claims,
            "runner_id": self.claiming_runner_id,
            "runtime_id": self.claiming_runtime_id,
            "last_claimed_task": self.last_claimed_task,
        }

    def pickup_safety_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.pickup_safety_started_at),
            "last_pickup_safety_at": fmt(self.last_pickup_safety_at),
            "pickup_safety_iteration": self.pickup_safety_iteration,
            "pickup_safety_enabled": self.pickup_safety_enabled,
            "pickup_safety_status": self.pickup_safety_status,
            "pickup_safety_interval_seconds": self.pickup_safety_interval_seconds,
            "pickup_safety_last_duration_ms": self.pickup_safety_last_duration_ms,
            "pickup_safety_errors": self.pickup_safety_errors,
            "pickup_safety_last_error": self.pickup_safety_last_error,
            "allows_pickup": self.pickup_safety_allows_pickup,
            "duplicate_prevention": self.pickup_safety_duplicate_prevention,
            "race_condition_controlled": (
                self.pickup_safety_race_condition_controlled
            ),
            "ownership_consistent": self.pickup_safety_ownership_consistent,
            "runtime_consistent": self.pickup_safety_runtime_consistent,
            "retry_allowed": self.pickup_safety_retry_allowed,
            "active_claims": self.pickup_safety_active_claims,
            "stale_claims": self.pickup_safety_stale_claims,
            "orphaned_claims": self.pickup_safety_orphaned_claims,
            "foreign_runtime_claims": self.pickup_safety_foreign_runtime_claims,
            "invalid_claims": self.pickup_safety_invalid_claims,
            "max_concurrent_claims": self.pickup_safety_max_concurrent_claims,
            "max_stale_claims": self.pickup_safety_max_stale_claims,
            "max_orphaned_claims": self.pickup_safety_max_orphaned_claims,
            "max_invalid_claims": self.pickup_safety_max_invalid_claims,
            "max_foreign_runtime_claims": (
                self.pickup_safety_max_foreign_runtime_claims
            ),
            "pickup_retry_attempts": self.pickup_safety_retry_attempts,
            "max_pickup_retries": self.pickup_safety_max_retries,
            "retry_window_seconds": self.pickup_safety_retry_window_seconds,
            "reasons": list(self.pickup_safety_reasons),
            "runner_id": self.pickup_safety_runner_id,
            "runtime_id": self.pickup_safety_runtime_id,
        }

    def execution_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.task_execution_started_at),
            "last_execution_at": fmt(self.last_execution_at),
            "execution_iteration": self.execution_iteration,
            "execution_enabled": self.execution_enabled,
            "execution_status": self.execution_status,
            "execution_interval_seconds": self.execution_interval_seconds,
            "execution_last_duration_ms": self.execution_last_duration_ms,
            "execution_errors": self.execution_errors,
            "execution_last_error": self.execution_last_error,
            "executions_prepared": self.executions_prepared,
            "executions_started": self.executions_started,
            "executions_completed": self.executions_completed,
            "executions_rejected": self.executions_rejected,
            "active_executions": self.active_executions,
            "max_concurrent_executions": self.max_concurrent_executions,
            "max_duration_seconds": self.max_execution_duration_seconds,
            "max_runtime_load": self.max_runtime_load,
            "runtime_load": self.runtime_load,
            "max_memory_mb": self.max_execution_memory_mb,
            "memory_usage_mb": self.execution_memory_usage_mb,
            "execution_id": self.last_execution_id,
            "execution_state": self.last_execution_state,
            "task_id": self.last_execution_task_id,
            "task_title": self.last_execution_task_title,
            "started_execution_at": self.last_execution_started_at,
            "finished_execution_at": self.last_execution_finished_at,
            "execution_duration_ms": self.last_execution_duration_ms,
            "runtime_owner": self.execution_runtime_owner,
            "reasons": list(self.execution_reasons),
        }

    def execution_session_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.execution_session_started_at),
            "last_execution_session_at": fmt(self.last_execution_session_at),
            "execution_session_iteration": self.execution_session_iteration,
            "execution_session_enabled": self.execution_session_enabled,
            "execution_session_status": self.execution_session_status,
            "session_state": self.execution_session_state,
            "execution_session_interval_seconds": (
                self.execution_session_interval_seconds
            ),
            "execution_session_last_duration_ms": (
                self.execution_session_last_duration_ms
            ),
            "execution_session_errors": self.execution_session_errors,
            "execution_session_last_error": self.execution_session_last_error,
            "runtime_protected": self.execution_session_runtime_protected,
            "active_sessions": self.execution_session_active_sessions,
            "max_active_sessions": self.execution_session_max_active_sessions,
            "max_log_entries": self.execution_session_max_log_entries,
            "recovery_available": self.execution_session_recovery_available,
            "runtime_owner": self.execution_session_runtime_owner,
            "session_id": self.last_execution_session_id,
            "task_id": self.last_execution_session_task_id,
            "phase_id": self.last_execution_session_phase_id,
            "audit_status": self.last_execution_session_audit_status,
            "last_checkpoint": self.last_execution_session_checkpoint,
            "last_action": self.last_execution_session_action,
            "last_file_modified": self.last_execution_session_file_modified,
            "last_result": self.last_execution_session_result,
            "last_error": self.last_execution_session_error_detail,
            "last_audit": self.last_execution_session_audit,
            "modified_files": list(self.execution_session_modified_files),
            "human_approval_status": (
                self.last_execution_session_human_approval_status
            ),
            "context_snapshot": self.execution_session_context_snapshot,
            "context_recovery_available": (
                self.execution_session_context_recovery_available
            ),
            "log_count": self.execution_session_log_count,
            "last_log": self.execution_session_last_log,
            "previous_state": self.last_execution_session_previous_state,
            "state_transition": self.last_execution_session_transition,
            "state_transition_allowed": (
                self.execution_session_transition_allowed
            ),
            "blocking_detected": self.execution_session_blocking_detected,
            "blocking_reasons": list(self.execution_session_blocking_reasons),
            "lifecycle_stage": self.last_execution_session_lifecycle_stage,
            "lifecycle_transition": (
                self.last_execution_session_lifecycle_transition
            ),
            "lifecycle_transition_allowed": (
                self.execution_session_lifecycle_transition_allowed
            ),
            "session": self.execution_session_snapshot,
            "reasons": list(self.execution_session_reasons),
        }

    def execution_safety_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.execution_safety_started_at),
            "last_execution_safety_at": fmt(self.last_execution_safety_at),
            "execution_safety_iteration": self.execution_safety_iteration,
            "execution_safety_enabled": self.execution_safety_enabled,
            "execution_safety_status": self.execution_safety_status,
            "execution_safety_interval_seconds": (
                self.execution_safety_interval_seconds
            ),
            "execution_safety_last_duration_ms": (
                self.execution_safety_last_duration_ms
            ),
            "execution_safety_errors": self.execution_safety_errors,
            "execution_safety_last_error": self.execution_safety_last_error,
            "allows_execution": self.execution_safety_allows_execution,
            "runtime_protected": self.execution_safety_runtime_protected,
            "conflict_detected": self.execution_conflict_detected,
            "timeout_detected": self.execution_timeout_detected,
            "provider_failure_detected": self.execution_provider_failure_detected,
            "retry_allowed": self.execution_retry_allowed,
            "retry_attempts": self.execution_retry_attempts,
            "max_retries": self.execution_max_retries,
            "active_executions": self.execution_safety_active_executions,
            "max_concurrent_executions": (
                self.execution_safety_max_concurrent_executions
            ),
            "runtime_load": self.execution_safety_runtime_load,
            "max_runtime_load": self.execution_safety_max_runtime_load,
            "memory_usage_mb": self.execution_safety_memory_usage_mb,
            "max_memory_mb": self.execution_safety_max_memory_mb,
            "active_provider_calls": self.execution_safety_active_provider_calls,
            "max_concurrent_provider_calls": (
                self.execution_safety_max_concurrent_provider_calls
            ),
            "provider_status": self.execution_safety_provider_status,
            "execution_status": self.execution_safety_execution_status,
            "execution_id": self.execution_safety_execution_id,
            "task_id": self.execution_safety_task_id,
            "checked_at": self.execution_safety_checked_at,
            "reasons": list(self.execution_safety_reasons),
        }

    def timeout_control_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.timeout_control_started_at),
            "last_timeout_control_at": fmt(self.last_timeout_control_at),
            "timeout_control_iteration": self.timeout_control_iteration,
            "timeout_control_enabled": self.timeout_control_enabled,
            "timeout_control_status": self.timeout_control_status,
            "timeout_state": self.timeout_state,
            "timeout_control_interval_seconds": (
                self.timeout_control_interval_seconds
            ),
            "timeout_control_last_duration_ms": (
                self.timeout_control_last_duration_ms
            ),
            "timeout_control_errors": self.timeout_control_errors,
            "timeout_control_last_error": self.timeout_control_last_error,
            "timeout_checks_passed": self.timeout_checks_passed,
            "timeout_checks_rejected": self.timeout_checks_rejected,
            "timeout_checks_failed": self.timeout_checks_failed,
            "timeouts_detected": self.timeouts_detected,
            "monitoring_allowed": self.timeout_monitoring_allowed,
            "runtime_protected": self.timeout_runtime_protected,
            "timeout_detected": self.timeout_detected,
            "timeout_registered": self.timeout_registered,
            "duration_tracking": self.timeout_duration_tracking,
            "linkage_valid": self.timeout_linkage_valid,
            "ownership_consistent": self.timeout_ownership_consistent,
            "active_timeout_checks": self.active_timeout_checks,
            "max_concurrent_timeout_checks": self.max_concurrent_timeout_checks,
            "runtime_timeout_load": self.runtime_timeout_load,
            "max_runtime_timeout_load": self.max_runtime_timeout_load,
            "max_tracking_duration_ms": self.max_timeout_tracking_duration_ms,
            "max_timeout_check_duration_ms": self.max_timeout_check_duration_ms,
            "timeout_id": self.last_timeout_id,
            "execution_id": self.last_timeout_execution_id,
            "task_id": self.last_timeout_task_id,
            "runtime_id": self.last_timeout_runtime_id,
            "runtime_owner": self.last_timeout_runtime_owner,
            "execution_state": self.last_timeout_execution_state,
            "execution_started_at": self.last_timeout_execution_started_at,
            "detected_at": self.last_timeout_detected_at,
            "checked_at": self.last_timeout_checked_at,
            "current_runtime_duration_ms": (
                self.timeout_execution_duration_ms
            ),
            "timeout_threshold_ms": self.timeout_threshold_ms,
            "metadata": dict(self.timeout_control_metadata),
            "reasons": list(self.timeout_control_reasons),
        }

    def retry_control_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.retry_control_started_at),
            "last_retry_control_at": fmt(self.last_retry_control_at),
            "retry_control_iteration": self.retry_control_iteration,
            "retry_control_enabled": self.retry_control_enabled,
            "retry_control_status": self.retry_control_status,
            "retry_state": self.retry_state,
            "retry_control_interval_seconds": self.retry_control_interval_seconds,
            "retry_control_last_duration_ms": (
                self.retry_control_last_duration_ms
            ),
            "retry_control_errors": self.retry_control_errors,
            "retry_control_last_error": self.retry_control_last_error,
            "retries_registered": self.retries_registered,
            "retries_started": self.retries_started,
            "retries_completed": self.retries_completed,
            "retries_rejected": self.retries_rejected,
            "retries_failed": self.retries_failed,
            "retry_allowed": self.retry_allowed,
            "runtime_protected": self.retry_runtime_protected,
            "linkage_valid": self.retry_linkage_valid,
            "ownership_consistent": self.retry_ownership_consistent,
            "threshold_valid": self.retry_threshold_valid,
            "provider_available": self.retry_provider_available,
            "active_retries": self.active_retries,
            "max_concurrent_retries": self.max_concurrent_retries,
            "runtime_retry_load": self.runtime_retry_load,
            "max_runtime_retry_load": self.max_runtime_retry_load,
            "max_retry_attempts": self.max_retry_attempts,
            "max_retry_duration_ms": self.max_retry_duration_ms,
            "max_retry_overhead_ms": self.max_retry_overhead_ms,
            "retry_id": self.last_retry_id,
            "execution_id": self.last_retry_execution_id,
            "task_id": self.last_retry_task_id,
            "runner_id": self.last_retry_runner_id,
            "runtime_id": self.last_retry_runtime_id,
            "runtime_owner": self.last_retry_runtime_owner,
            "execution_state": self.last_retry_execution_state,
            "task_status": self.last_retry_task_status,
            "provider_status": self.last_retry_provider_status,
            "retry_attempt": self.last_retry_attempt,
            "retry_threshold": self.last_retry_threshold,
            "retry_reason": self.last_retry_reason,
            "retry_started_at": self.last_retry_started_at,
            "retry_completed_at": self.last_retry_completed_at,
            "retry_duration_ms": self.last_retry_duration_ms,
            "metadata": dict(self.retry_control_metadata),
            "reasons": list(self.retry_control_reasons),
        }

    def orchestration_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.orchestration_started_at),
            "last_orchestration_at": fmt(self.last_orchestration_at),
            "orchestration_iteration": self.orchestration_iteration,
            "orchestration_enabled": self.orchestration_enabled,
            "orchestration_status": self.orchestration_status,
            "orchestration_state": self.orchestration_state,
            "dependency_state": self.dependency_state,
            "coordination_state": self.orchestration_state,
            "dependency_status": self.dependency_state,
            "orchestration_interval_seconds": (
                self.orchestration_interval_seconds
            ),
            "orchestration_last_duration_ms": (
                self.orchestration_last_duration_ms
            ),
            "orchestration_errors": self.orchestration_errors,
            "orchestration_last_error": self.orchestration_last_error,
            "orchestrations_registered": self.orchestrations_registered,
            "orchestrations_started": self.orchestrations_started,
            "orchestrations_completed": self.orchestrations_completed,
            "orchestrations_released": self.orchestrations_released,
            "orchestrations_rejected": self.orchestrations_rejected,
            "orchestrations_failed": self.orchestrations_failed,
            "coordination_allowed": self.coordination_allowed,
            "runtime_protected": self.orchestration_runtime_protected,
            "conflict_detected": self.orchestration_conflict_detected,
            "linkage_valid": self.orchestration_linkage_valid,
            "ownership_consistent": self.orchestration_ownership_consistent,
            "dependency_valid": self.orchestration_dependency_valid,
            "active_orchestrations": self.active_orchestrations,
            "max_active_orchestrations": self.max_active_orchestrations,
            "runtime_orchestration_load": self.runtime_orchestration_load,
            "max_orchestration_load": self.max_orchestration_load,
            "max_execution_dependencies": self.max_execution_dependencies,
            "max_dependency_chain": self.max_dependency_chain,
            "max_orchestration_duration_ms": (
                self.max_orchestration_duration_ms
            ),
            "max_coordination_overhead_ms": self.max_coordination_overhead_ms,
            "orchestration_id": self.last_orchestration_id,
            "coordination_id": self.last_orchestration_id,
            "execution_id": self.last_orchestration_execution_id,
            "task_id": self.last_orchestration_task_id,
            "runner_id": self.last_orchestration_runner_id,
            "runtime_id": self.last_orchestration_runtime_id,
            "runtime_owner": self.last_orchestration_runtime_owner,
            "execution_state": self.last_orchestration_execution_state,
            "task_status": self.last_orchestration_task_status,
            "execution_order": self.last_orchestration_execution_order,
            "execution_sequence": self.last_orchestration_execution_order,
            "dependency_count": self.last_orchestration_dependency_count,
            "coordination_started_at": self.last_coordination_started_at,
            "coordination_completed_at": self.last_coordination_completed_at,
            "coordination_duration_ms": self.last_coordination_duration_ms,
            "dependencies": [dict(item) for item in self.orchestration_dependencies],
            "metadata": dict(self.orchestration_metadata),
            "reasons": list(self.orchestration_reasons),
        }

    def orchestration_safety_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.orchestration_safety_started_at),
            "last_orchestration_safety_at": fmt(
                self.last_orchestration_safety_at
            ),
            "orchestration_safety_iteration": (
                self.orchestration_safety_iteration
            ),
            "orchestration_safety_enabled": self.orchestration_safety_enabled,
            "orchestration_safety_status": self.orchestration_safety_status,
            "safety_state": self.orchestration_safety_state,
            "orchestration_safety_interval_seconds": (
                self.orchestration_safety_interval_seconds
            ),
            "orchestration_safety_last_duration_ms": (
                self.orchestration_safety_last_duration_ms
            ),
            "orchestration_safety_errors": self.orchestration_safety_errors,
            "orchestration_safety_last_error": (
                self.orchestration_safety_last_error
            ),
            "allows_orchestration": (
                self.orchestration_safety_allows_orchestration
            ),
            "runtime_protected": self.orchestration_safety_runtime_protected,
            "conflict_detected": (
                self.orchestration_safety_conflict_detected
            ),
            "dependency_corruption_detected": (
                self.orchestration_safety_dependency_corruption_detected
            ),
            "sequencing_violation_detected": (
                self.orchestration_safety_sequencing_violation_detected
            ),
            "runaway_detected": self.orchestration_safety_runaway_detected,
            "timeout_detected": self.orchestration_safety_timeout_detected,
            "retry_allowed": self.orchestration_safety_retry_allowed,
            "retry_attempts": self.orchestration_safety_retry_attempts,
            "max_retries": self.orchestration_safety_max_retries,
            "active_orchestrations": (
                self.orchestration_safety_active_orchestrations
            ),
            "max_active_orchestrations": (
                self.orchestration_safety_max_active_orchestrations
            ),
            "runtime_orchestration_load": (
                self.orchestration_safety_runtime_load
            ),
            "max_orchestration_load": (
                self.orchestration_safety_max_runtime_load
            ),
            "coordination_duration_ms": (
                self.orchestration_safety_coordination_duration_ms
            ),
            "max_orchestration_duration_ms": (
                self.orchestration_safety_max_duration_ms
            ),
            "coordination_overhead_ms": (
                self.orchestration_safety_coordination_overhead_ms
            ),
            "max_coordination_overhead_ms": (
                self.orchestration_safety_max_overhead_ms
            ),
            "safety_id": self.last_orchestration_safety_id,
            "coordination_id": self.orchestration_safety_coordination_id,
            "execution_id": self.orchestration_safety_execution_id,
            "task_id": self.orchestration_safety_task_id,
            "runtime_owner": self.orchestration_safety_runtime_owner,
            "dependencies": [
                dict(item) for item in self.orchestration_safety_dependencies
            ],
            "metadata": dict(self.orchestration_safety_metadata),
            "reasons": list(self.orchestration_safety_reasons),
        }

    def provider_bridge_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.provider_bridge_started_at),
            "last_provider_bridge_at": fmt(self.last_provider_bridge_at),
            "provider_bridge_iteration": self.provider_bridge_iteration,
            "provider_bridge_enabled": self.provider_bridge_enabled,
            "provider_bridge_status": self.provider_bridge_status,
            "provider_bridge_interval_seconds": self.provider_bridge_interval_seconds,
            "provider_bridge_last_duration_ms": self.provider_bridge_last_duration_ms,
            "provider_bridge_errors": self.provider_bridge_errors,
            "provider_bridge_last_error": self.provider_bridge_last_error,
            "provider_requests_completed": self.provider_requests_completed,
            "provider_requests_rejected": self.provider_requests_rejected,
            "provider_requests_failed": self.provider_requests_failed,
            "provider_timeouts": self.provider_timeouts,
            "provider_invalid_responses": self.provider_invalid_responses,
            "active_provider_calls": self.active_provider_calls,
            "active_provider_sessions": self.active_provider_sessions,
            "max_concurrent_provider_calls": self.max_concurrent_provider_calls,
            "max_requests_per_minute": self.max_provider_requests_per_minute,
            "requests_in_window": self.provider_requests_in_window,
            "max_request_bytes": self.max_provider_request_bytes,
            "request_size_bytes": self.provider_request_size_bytes,
            "timeout_seconds": self.provider_timeout_seconds,
            "max_response_bytes": self.max_provider_response_bytes,
            "response_size_bytes": self.provider_response_size_bytes,
            "provider_name": self.provider_name,
            "provider_session_id": self.provider_session_id,
            "connection_status": self.provider_connection_status,
            "failure_status": self.provider_failure_status,
            "connection_states": list(self.provider_connection_states),
            "model": self.provider_model,
            "request_id": self.provider_request_id,
            "execution_id": self.provider_execution_id,
            "task_id": self.provider_task_id,
            "started_request_at": self.provider_started_at,
            "finished_request_at": self.provider_finished_at,
            "provider_duration_ms": self.provider_duration_ms,
            "usage": dict(self.provider_usage),
            "input_tokens": self.provider_input_tokens,
            "output_tokens": self.provider_output_tokens,
            "total_tokens": self.provider_total_tokens,
            "reasons": list(self.provider_bridge_reasons),
        }

    def response_ingestion_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.response_ingestion_started_at),
            "last_response_ingestion_at": fmt(self.last_response_ingestion_at),
            "response_ingestion_iteration": self.response_ingestion_iteration,
            "response_ingestion_enabled": self.response_ingestion_enabled,
            "response_ingestion_status": self.response_ingestion_status,
            "ingestion_state": self.response_ingestion_state,
            "response_ingestion_interval_seconds": (
                self.response_ingestion_interval_seconds
            ),
            "response_ingestion_last_duration_ms": (
                self.response_ingestion_last_duration_ms
            ),
            "response_ingestion_errors": self.response_ingestion_errors,
            "response_ingestion_last_error": self.response_ingestion_last_error,
            "responses_received": self.responses_received,
            "responses_ingested": self.responses_ingested,
            "responses_rejected": self.responses_rejected,
            "responses_failed": self.responses_failed,
            "active_ingestions": self.active_response_ingestions,
            "max_concurrent_ingestions": (
                self.max_concurrent_response_ingestions
            ),
            "max_response_bytes": self.max_response_ingestion_bytes,
            "response_size_bytes": self.response_ingestion_size_bytes,
            "max_ingestion_duration_ms": (
                self.max_response_ingestion_duration_ms
            ),
            "runtime_ingestion_load": self.response_ingestion_runtime_load,
            "max_runtime_ingestion_load": (
                self.max_response_ingestion_runtime_load
            ),
            "response_id": self.last_response_id,
            "execution_id": self.last_response_execution_id,
            "task_id": self.last_response_task_id,
            "runtime_id": self.last_response_runtime_id,
            "execution_owner": self.last_response_execution_owner,
            "provider_source": self.last_response_provider_source,
            "provider_request_id": self.last_response_provider_request_id,
            "model": self.last_response_model,
            "received_at": self.last_response_received_at,
            "started_at_response": self.last_response_started_at,
            "finished_at_response": self.last_response_finished_at,
            "storage_prepared": self.response_storage_prepared,
            "metadata": dict(self.response_ingestion_metadata),
            "reasons": list(self.response_ingestion_reasons),
        }

    def response_validation_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.response_validation_started_at),
            "last_response_validation_at": fmt(self.last_response_validation_at),
            "response_validation_iteration": self.response_validation_iteration,
            "response_validation_enabled": self.response_validation_enabled,
            "response_validation_status": self.response_validation_status,
            "validation_state": self.response_validation_state,
            "response_validation_interval_seconds": (
                self.response_validation_interval_seconds
            ),
            "response_validation_last_duration_ms": (
                self.response_validation_last_duration_ms
            ),
            "response_validation_errors": self.response_validation_errors,
            "response_validation_last_error": self.response_validation_last_error,
            "responses_validated": self.responses_validated,
            "responses_rejected": self.responses_validation_rejected,
            "responses_failed": self.responses_validation_failed,
            "active_validations": self.active_response_validations,
            "max_concurrent_validations": (
                self.max_concurrent_response_validations
            ),
            "max_payload_inspection_bytes": (
                self.max_response_validation_payload_bytes
            ),
            "payload_size_bytes": self.response_validation_payload_size_bytes,
            "max_validation_duration_ms": (
                self.max_response_validation_duration_ms
            ),
            "runtime_validation_load": self.response_validation_runtime_load,
            "max_runtime_validation_load": (
                self.max_response_validation_runtime_load
            ),
            "validation_id": self.last_validation_id,
            "execution_id": self.last_validation_execution_id,
            "task_id": self.last_validation_task_id,
            "runtime_id": self.last_validation_runtime_id,
            "execution_owner": self.last_validation_execution_owner,
            "provider_source": self.last_validation_provider_source,
            "provider_request_id": self.last_validation_provider_request_id,
            "model": self.last_validation_model,
            "validated_at": self.last_validation_validated_at,
            "started_at_validation": self.last_validation_started_at,
            "finished_at_validation": self.last_validation_finished_at,
            "metadata": dict(self.response_validation_metadata),
            "reasons": list(self.response_validation_reasons),
        }

    def response_safety_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "started_at": fmt(self.response_safety_started_at),
            "last_response_safety_at": fmt(self.last_response_safety_at),
            "response_safety_iteration": self.response_safety_iteration,
            "response_safety_enabled": self.response_safety_enabled,
            "response_safety_status": self.response_safety_status,
            "safety_state": self.response_safety_state,
            "response_safety_interval_seconds": self.response_safety_interval_seconds,
            "response_safety_last_duration_ms": (
                self.response_safety_last_duration_ms
            ),
            "response_safety_errors": self.response_safety_errors,
            "response_safety_last_error": self.response_safety_last_error,
            "responses_safe": self.responses_safety_passed,
            "responses_blocked": self.responses_safety_blocked,
            "responses_failed": self.responses_safety_failed,
            "allows_response": self.response_safety_allows_response,
            "runtime_protected": self.response_safety_runtime_protected,
            "corrupted_detected": self.response_safety_corrupted_detected,
            "poisoning_detected": self.response_safety_poisoning_detected,
            "timeout_detected": self.response_safety_timeout_detected,
            "provider_failure_detected": (
                self.response_safety_provider_failure_detected
            ),
            "retry_allowed": self.response_safety_retry_allowed,
            "retry_attempts": self.response_safety_retry_attempts,
            "max_validation_retries": (
                self.response_safety_max_validation_retries
            ),
            "active_safety_checks": self.active_response_safety_checks,
            "max_concurrent_safety_checks": (
                self.max_concurrent_response_safety_checks
            ),
            "max_payload_bytes": self.max_response_safety_payload_bytes,
            "payload_size_bytes": self.response_safety_payload_size_bytes,
            "max_safety_duration_ms": self.max_response_safety_duration_ms,
            "runtime_safety_load": self.response_safety_runtime_load,
            "max_runtime_safety_load": self.max_response_safety_runtime_load,
            "safety_id": self.last_safety_id,
            "execution_id": self.last_safety_execution_id,
            "task_id": self.last_safety_task_id,
            "runtime_id": self.last_safety_runtime_id,
            "execution_owner": self.last_safety_execution_owner,
            "provider_source": self.last_safety_provider_source,
            "provider_request_id": self.last_safety_provider_request_id,
            "model": self.last_safety_model,
            "checked_at": self.last_safety_checked_at,
            "started_at_safety": self.last_safety_started_at,
            "finished_at_safety": self.last_safety_finished_at,
            "metadata": dict(self.response_safety_metadata),
            "reasons": list(self.response_safety_reasons),
        }

    def to_dict(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        data = {
            "runner_alive": self.runner_alive,
            "runner_status": self.health_status(),
            "runner_started_at": fmt(self.runner_started_at),
            "last_loop_at": fmt(self.last_loop_at),
            "last_task_started_at": fmt(self.last_task_started_at),
            "last_task_completed_at": fmt(self.last_task_completed_at),
            "current_task_id": self.current_task_id,
            "current_task_title": self.current_task_title,
            "total_processed": self.total_processed,
            "total_success": self.total_success,
            "total_failed": self.total_failed,
            "runtime_loop": self.runtime_loop_metrics(),
            "polling": self.polling_metrics(),
            "discovery": self.discovery_metrics(),
            "claiming": self.claiming_metrics(),
            "pickup_safety": self.pickup_safety_metrics(),
            "execution": self.execution_metrics(),
            "execution_session": self.execution_session_metrics(),
            "execution_safety": self.execution_safety_metrics(),
            "timeout_control": self.timeout_control_metrics(),
            "retry_control": self.retry_control_metrics(),
            "orchestration": self.orchestration_metrics(),
            "orchestration_safety": self.orchestration_safety_metrics(),
            "provider_bridge": self.provider_bridge_metrics(),
            "response_ingestion": self.response_ingestion_metrics(),
            "response_validation": self.response_validation_metrics(),
            "response_safety": self.response_safety_metrics(),
            "safety": self.safety_metrics(),
        }
        data.update(self.ai_metrics())
        data.update(self.telegram_metrics())
        return data


runtime_status = RuntimeStatus()
