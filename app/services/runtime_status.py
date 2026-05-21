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
        self.last_prompt_execution_at: datetime | None = None
        self.prompt_execution_iteration = 0
        self.prompt_execution_status = "stopped"
        self.prompt_execution_prompt_status: str | None = None
        self.prompt_executions_completed = 0
        self.prompt_executions_rejected = 0
        self.prompt_executions_failed = 0
        self.last_prompt_execution_id: str | None = None
        self.prompt_execution_type: str | None = None
        self.prompt_execution_objective: str | None = None
        self.prompt_execution_provider: str | None = None
        self.prompt_execution_provider_session_id: str | None = None
        self.prompt_execution_request_id: str | None = None
        self.prompt_execution_execution_id: str | None = None
        self.prompt_execution_task_id: str | None = None
        self.prompt_execution_prompt_size_bytes = 0
        self.prompt_execution_output_available = False
        self.prompt_execution_output_size_bytes = 0
        self.prompt_execution_duration_ms = 0
        self.prompt_execution_provider_duration_ms = 0
        self.prompt_execution_usage: dict = {}
        self.prompt_execution_reasons: list[str] = []
        self.prompt_execution_last_error: str | None = None
        self.prompt_execution_lifecycle: list[dict] = []
        self.last_provider_response_handling_at: datetime | None = None
        self.provider_response_handling_iteration = 0
        self.provider_response_handling_status = "stopped"
        self.provider_response_status: str | None = None
        self.provider_response_type: str | None = None
        self.provider_responses_handled = 0
        self.provider_responses_rejected = 0
        self.provider_responses_failed = 0
        self.last_provider_response_handling_id: str | None = None
        self.last_provider_response_id: str | None = None
        self.provider_response_provider_id: str | None = None
        self.provider_response_request_id: str | None = None
        self.provider_response_execution_id: str | None = None
        self.provider_response_task_id: str | None = None
        self.provider_response_validation_status: str | None = None
        self.provider_response_audit_status = "not_ready"
        self.provider_response_output_available = False
        self.provider_response_output_size_bytes = 0
        self.provider_response_storage_prepared = False
        self.provider_response_duration_ms = 0
        self.provider_response_audit_package: dict = {}
        self.provider_response_reasons: list[str] = []
        self.provider_response_last_error: str | None = None
        self.provider_response_lifecycle: list[dict] = []
        self.last_provider_failure_control_at: datetime | None = None
        self.provider_failure_control_iteration = 0
        self.provider_failure_control_status = "stopped"
        self.provider_failure_detected = False
        self.provider_failures_detected = 0
        self.provider_failures_contained = 0
        self.provider_failures_blocked = 0
        self.provider_failures_escalated = 0
        self.provider_failure_control_errors = 0
        self.last_provider_failure_id: str | None = None
        self.provider_failure_provider_id: str | None = None
        self.provider_failure_execution_id: str | None = None
        self.provider_failure_task_id: str | None = None
        self.provider_failure_request_id: str | None = None
        self.provider_failure_session_id: str | None = None
        self.provider_failure_type: str | None = None
        self.provider_failure_severity: str | None = None
        self.provider_failure_state: str | None = None
        self.provider_failure_recovery_status = "not_required"
        self.provider_failure_runtime_state: str | None = None
        self.provider_failure_execution_impact = "none"
        self.provider_failure_continuation_blocked = False
        self.provider_failure_context_preserved = True
        self.provider_failure_recovery_prepared = False
        self.provider_failure_escalation_required = False
        self.provider_failure_duration_ms = 0
        self.provider_failure_timestamps: dict = {}
        self.provider_failure_lifecycle: list[dict] = []
        self.provider_failure_reasons: list[str] = []
        self.provider_failure_last_error: str | None = None
        self.provider_failure_metadata: dict = {}
        self.last_provider_routing_at: datetime | None = None
        self.provider_routing_iteration = 0
        self.provider_routing_status = "stopped"
        self.provider_routes_selected = 0
        self.provider_routes_blocked = 0
        self.provider_routes_degraded = 0
        self.provider_routing_errors = 0
        self.last_provider_routing_id: str | None = None
        self.provider_routing_type: str | None = None
        self.provider_routing_task_type: str | None = None
        self.provider_routing_selected_provider: str | None = None
        self.provider_routing_cost_estimate: str | None = None
        self.provider_routing_execution_priority: str | None = None
        self.provider_routing_reason: str | None = None
        self.provider_routing_fallback_status: str | None = None
        self.provider_routing_fallback_provider: str | None = None
        self.provider_routing_provider_degraded = False
        self.provider_routing_quality_estimate: str | None = None
        self.provider_routing_execution_mode: str | None = None
        self.provider_routing_runtime_limits: dict = {}
        self.provider_routing_available_providers: list[str] = []
        self.provider_routing_blocked_providers: list[str] = []
        self.provider_routing_evaluated_providers: list[dict] = []
        self.provider_routing_selected_health: dict = {}
        self.provider_routing_fallback_health: dict = {}
        self.provider_routing_conflict = False
        self.provider_routing_duration_ms = 0
        self.provider_routing_reasons: list[str] = []
        self.provider_routing_last_error: str | None = None
        self.provider_routing_metadata: dict = {}
        self.last_self_validation_at: datetime | None = None
        self.self_validation_iteration = 0
        self.self_validation_status = "stopped"
        self.self_validations_valid = 0
        self.self_validations_warning = 0
        self.self_validations_invalid = 0
        self.self_validation_errors = 0
        self.last_self_validation_id: str | None = None
        self.self_validation_execution_id: str | None = None
        self.self_validation_task_id: str | None = None
        self.self_validation_risk_status: str | None = None
        self.self_validation_audit_required = False
        self.self_validation_self_approved = False
        self.self_validation_continuation_blocked = False
        self.self_validation_runtime_protected = True
        self.self_validation_modified_files: list[str] = []
        self.self_validation_logs: list[dict] = []
        self.self_validation_detected_risks: list[str] = []
        self.self_validation_inconsistencies: list[str] = []
        self.self_validation_audit_package: dict = {}
        self.self_validation_output_count = 0
        self.self_validation_response_count = 0
        self.self_validation_duration_ms = 0
        self.self_validation_reasons: list[str] = []
        self.self_validation_last_error: str | None = None
        self.self_validation_metadata: dict = {}
        self.last_audit_request_at: datetime | None = None
        self.audit_request_iteration = 0
        self.audit_request_status = "stopped"
        self.audit_requests_pending = 0
        self.audit_requests_blocked = 0
        self.audit_request_errors = 0
        self.last_audit_request_id: str | None = None
        self.audit_request_execution_id: str | None = None
        self.audit_request_task_id: str | None = None
        self.audit_request_type: str | None = None
        self.audit_request_audit_status: str | None = None
        self.audit_request_validation_status: str | None = None
        self.audit_request_risk_status: str | None = None
        self.audit_request_package: dict = {}
        self.audit_request_package_hash: str | None = None
        self.audit_request_continuation_frozen = False
        self.audit_request_continuation_status: str | None = None
        self.audit_request_traceability_preserved = False
        self.audit_request_delivery_targets: list[str] = []
        self.audit_request_delivery_status: str | None = None
        self.audit_request_lifecycle: list[dict] = []
        self.audit_request_modified_files: list[str] = []
        self.audit_request_detected_risks: list[str] = []
        self.audit_request_provider_context: dict = {}
        self.audit_request_runtime_state: dict = {}
        self.audit_request_duration_ms = 0
        self.audit_request_reasons: list[str] = []
        self.audit_request_last_error: str | None = None
        self.audit_request_metadata: dict = {}
        self.last_audit_response_at: datetime | None = None
        self.audit_response_iteration = 0
        self.audit_response_status = "stopped"
        self.audit_responses_approved = 0
        self.audit_responses_warning = 0
        self.audit_responses_needs_fix = 0
        self.audit_responses_rejected = 0
        self.audit_response_errors = 0
        self.last_audit_response_id: str | None = None
        self.audit_response_audit_id: str | None = None
        self.audit_response_execution_id: str | None = None
        self.audit_response_task_id: str | None = None
        self.audit_response_result: str | None = None
        self.audit_response_risk_level: str | None = None
        self.audit_response_correction_status: str | None = None
        self.audit_response_continuation_status: str | None = None
        self.audit_response_human_approval_status: str | None = None
        self.audit_response_security_escalation_status: str | None = None
        self.audit_response_centinela_escalation = False
        self.audit_response_execution_decision: str | None = None
        self.audit_response_context_preserved = False
        self.audit_response_integrity_preserved = False
        self.audit_response_warnings: list[str] = []
        self.audit_response_detected_risks: list[str] = []
        self.audit_response_rejection_reasons: list[str] = []
        self.audit_response_correction_requirements: list[str] = []
        self.audit_response_modified_files: list[str] = []
        self.audit_response_logs: list[dict] = []
        self.audit_response_lifecycle: list[dict] = []
        self.audit_response_execution_context: dict = {}
        self.audit_response_duration_ms = 0
        self.audit_response_reasons: list[str] = []
        self.audit_response_last_error: str | None = None
        self.audit_response_metadata: dict = {}
        self.last_approval_gate_at: datetime | None = None
        self.approval_gate_iteration = 0
        self.approval_gate_status = "stopped"
        self.approval_requests_pending = 0
        self.approval_decisions_approved = 0
        self.approval_decisions_rejected = 0
        self.approval_decisions_needs_changes = 0
        self.approval_decisions_escalated = 0
        self.approval_gate_errors = 0
        self.last_approval_id: str | None = None
        self.approval_gate_execution_id: str | None = None
        self.approval_gate_task_id: str | None = None
        self.approval_gate_type: str | None = None
        self.approval_gate_approval_status: str | None = None
        self.approval_gate_audit_status: str | None = None
        self.approval_gate_human_decision: str | None = None
        self.approval_gate_continuation_status: str | None = None
        self.approval_gate_risk_status: str | None = None
        self.approval_gate_governance_status: str | None = None
        self.approval_gate_context_preserved = False
        self.approval_gate_human_authority_preserved = False
        self.approval_gate_autonomy_blocked = True
        self.approval_gate_decided_by: str | None = None
        self.approval_gate_decision_reason: str = ""
        self.approval_gate_human_report: dict = {}
        self.approval_gate_modified_files: list[str] = []
        self.approval_gate_detected_risks: list[str] = []
        self.approval_gate_warnings: list[str] = []
        self.approval_gate_lifecycle: list[dict] = []
        self.approval_gate_execution_context: dict = {}
        self.approval_gate_duration_ms = 0
        self.approval_gate_reasons: list[str] = []
        self.approval_gate_last_error: str | None = None
        self.approval_gate_metadata: dict = {}
        self.last_execution_blocking_at: datetime | None = None
        self.execution_blocking_iteration = 0
        self.execution_blocking_status = "stopped"
        self.execution_blocks_active = 0
        self.execution_blocks_invalid = 0
        self.execution_blocking_errors = 0
        self.last_execution_block_id: str | None = None
        self.execution_block_execution_id: str | None = None
        self.execution_block_task_id: str | None = None
        self.execution_block_type: str | None = None
        self.execution_block_status: str | None = None
        self.execution_block_classification: str | None = None
        self.execution_block_reason: str | None = None
        self.execution_block_risk_level: str | None = None
        self.execution_block_escalation_status: str | None = None
        self.execution_block_continuation_status: str | None = None
        self.execution_block_execution_frozen = False
        self.execution_block_continuation_blocked = False
        self.execution_block_context_preserved = False
        self.execution_block_governance_protected = False
        self.execution_block_security_authority_required = False
        self.execution_block_human_authority_required = False
        self.execution_block_modified_files: list[str] = []
        self.execution_block_runtime_logs: list[dict] = []
        self.execution_block_audit_history: list[dict] = []
        self.execution_block_risk_history: list[str] = []
        self.execution_block_runtime_state: dict = {}
        self.execution_block_provider_context: dict = {}
        self.execution_block_execution_context: dict = {}
        self.execution_block_lifecycle: list[dict] = []
        self.execution_block_duration_ms = 0
        self.execution_block_reasons: list[str] = []
        self.execution_block_last_error: str | None = None
        self.execution_block_metadata: dict = {}
        self.last_phase_continuation_at: datetime | None = None
        self.phase_continuation_iteration = 0
        self.phase_continuation_status = "stopped"
        self.phase_continuations_ready = 0
        self.phase_continuations_blocked = 0
        self.phase_continuations_completed = 0
        self.phase_continuation_errors = 0
        self.last_phase_continuation_id: str | None = None
        self.phase_continuation_current_phase: str | None = None
        self.phase_continuation_current_subphase: str | None = None
        self.phase_continuation_next_subphase: str | None = None
        self.phase_continuation_type: str | None = None
        self.phase_continuation_governance_status: str | None = None
        self.phase_continuation_audit_status: str | None = None
        self.phase_continuation_execution_status: str | None = None
        self.phase_continuation_runtime_status: str | None = None
        self.phase_continuation_roadmap_loaded = False
        self.phase_continuation_dependencies_satisfied = False
        self.phase_continuation_governance_satisfied = False
        self.phase_continuation_audit_satisfied = False
        self.phase_continuation_execution_stable = False
        self.phase_continuation_runtime_safe = False
        self.phase_continuation_context_preserved = False
        self.phase_continuation_traceability_preserved = False
        self.phase_continuation_progression_allowed = False
        self.phase_continuation_roadmap: list[str] = []
        self.phase_continuation_completed_subphases: list[str] = []
        self.phase_continuation_required_dependencies: list[str] = []
        self.phase_continuation_missing_dependencies: list[str] = []
        self.phase_continuation_execution_context: dict = {}
        self.phase_continuation_lifecycle_history: list[dict] = []
        self.phase_continuation_audit_history: list[dict] = []
        self.phase_continuation_governance_history: list[dict] = []
        self.phase_continuation_lifecycle: list[dict] = []
        self.phase_continuation_duration_ms = 0
        self.phase_continuation_reasons: list[str] = []
        self.phase_continuation_last_error: str | None = None
        self.phase_continuation_metadata: dict = {}
        self.last_checkpoint_recovery_at: datetime | None = None
        self.checkpoint_recovery_iteration = 0
        self.checkpoint_recovery_status = "stopped"
        self.checkpoints_created = 0
        self.checkpoint_recoveries_prepared = 0
        self.checkpoint_recoveries_blocked = 0
        self.checkpoint_recovery_errors = 0
        self.last_checkpoint_id: str | None = None
        self.last_recovery_id: str | None = None
        self.checkpoint_execution_id: str | None = None
        self.checkpoint_task_id: str | None = None
        self.checkpoint_type: str | None = None
        self.checkpoint_recovery_state: str | None = None
        self.checkpoint_valid = False
        self.checkpoint_checksum: str | None = None
        self.checkpoint_restoration_ready = False
        self.checkpoint_continuation_status: str | None = None
        self.checkpoint_context_preserved = False
        self.checkpoint_traceability_preserved = False
        self.checkpoint_governance_review_required = False
        self.checkpoint_audit_review_required = False
        self.checkpoint_payload: dict = {}
        self.checkpoint_restored_state: dict = {}
        self.checkpoint_phase_state: dict = {}
        self.checkpoint_runtime_state: dict = {}
        self.checkpoint_governance_state: dict = {}
        self.checkpoint_audit_state: dict = {}
        self.checkpoint_provider_state: dict = {}
        self.checkpoint_execution_context: dict = {}
        self.checkpoint_lifecycle_state: dict = {}
        self.checkpoint_modified_files: list[str] = []
        self.checkpoint_recovery_logs: list[dict] = []
        self.checkpoint_recovery_lifecycle: list[dict] = []
        self.checkpoint_recovery_duration_ms = 0
        self.checkpoint_recovery_reasons: list[str] = []
        self.checkpoint_recovery_last_error: str | None = None
        self.checkpoint_recovery_metadata: dict = {}
        self.last_execution_resume_at: datetime | None = None
        self.execution_resume_iteration = 0
        self.execution_resume_status = "stopped"
        self.execution_resumes_completed = 0
        self.execution_resumes_blocked = 0
        self.execution_resume_errors = 0
        self.last_resume_id: str | None = None
        self.resume_execution_id: str | None = None
        self.resume_task_id: str | None = None
        self.resume_checkpoint_id: str | None = None
        self.resume_type: str | None = None
        self.resume_governance_status: str | None = None
        self.resume_audit_status: str | None = None
        self.resume_state: str | None = None
        self.resume_continuation_status: str | None = None
        self.resume_runtime_stable = False
        self.resume_checkpoint_valid = False
        self.resume_execution_consistent = False
        self.resume_governance_satisfied = False
        self.resume_audit_satisfied = False
        self.resume_workflow_continuity_preserved = False
        self.resume_execution_reactivated = False
        self.resume_context_restored = False
        self.resume_context_preserved = False
        self.resume_traceability_preserved = False
        self.resume_provider_context_restored = False
        self.resume_restored_state: dict = {}
        self.resume_execution_context: dict = {}
        self.resume_lifecycle_state: dict = {}
        self.resume_runtime_state: dict = {}
        self.resume_governance_state: dict = {}
        self.resume_audit_state: dict = {}
        self.resume_provider_state: dict = {}
        self.resume_lifecycle_history: list[dict] = []
        self.resume_audit_history: list[dict] = []
        self.resume_governance_history: list[dict] = []
        self.resume_recovery_history: list[dict] = []
        self.resume_modified_files: list[str] = []
        self.resume_lifecycle: list[dict] = []
        self.execution_resume_duration_ms = 0
        self.execution_resume_reasons: list[str] = []
        self.execution_resume_last_error: str | None = None
        self.execution_resume_metadata: dict = {}
        self.last_workflow_chaining_at: datetime | None = None
        self.workflow_chaining_iteration = 0
        self.workflow_chaining_status = "stopped"
        self.workflow_chains_activated = 0
        self.workflow_chains_blocked = 0
        self.workflow_chains_completed = 0
        self.workflow_chaining_errors = 0
        self.last_chaining_id: str | None = None
        self.chaining_current_workflow: str | None = None
        self.chaining_next_workflow: str | None = None
        self.chaining_current_phase: str | None = None
        self.chaining_current_subphase: str | None = None
        self.chaining_type: str | None = None
        self.chaining_governance_status: str | None = None
        self.chaining_audit_status: str | None = None
        self.chaining_execution_status: str | None = None
        self.chaining_dependency_status: str | None = None
        self.chaining_continuation_status: str | None = None
        self.chaining_roadmap_loaded = False
        self.chaining_current_workflow_completed = False
        self.chaining_dependencies_satisfied = False
        self.chaining_governance_satisfied = False
        self.chaining_audit_satisfied = False
        self.chaining_execution_stable = False
        self.chaining_runtime_safe = False
        self.chaining_progression_allowed = False
        self.chaining_workflow_activation = False
        self.chaining_context_preserved = False
        self.chaining_traceability_preserved = False
        self.chaining_roadmap: list[str] = []
        self.chaining_completed_workflows: list[str] = []
        self.chaining_required_dependencies: list[str] = []
        self.chaining_missing_dependencies: list[str] = []
        self.chaining_next_workflow_context: dict = {}
        self.chaining_execution_context: dict = {}
        self.chaining_lifecycle_history: list[dict] = []
        self.chaining_roadmap_history: list[dict] = []
        self.chaining_governance_history: list[dict] = []
        self.chaining_audit_history: list[dict] = []
        self.chaining_lifecycle: list[dict] = []
        self.workflow_chaining_duration_ms = 0
        self.workflow_chaining_reasons: list[str] = []
        self.workflow_chaining_last_error: str | None = None
        self.workflow_chaining_metadata: dict = {}
        self.last_continuation_safety_at: datetime | None = None
        self.continuation_safety_iteration = 0
        self.continuation_safety_status = "stopped"
        self.continuations_safe = 0
        self.continuations_warning = 0
        self.continuations_blocked = 0
        self.continuations_critical = 0
        self.continuation_safety_errors = 0
        self.last_safety_id: str | None = None
        self.safety_execution_id: str | None = None
        self.safety_task_id: str | None = None
        self.safety_type: str | None = None
        self.safety_current_workflow: str | None = None
        self.safety_next_workflow: str | None = None
        self.safety_continuation_status: str | None = None
        self.safety_governance_status: str | None = None
        self.safety_audit_status: str | None = None
        self.safety_security_status: str | None = None
        self.safety_risk_level: str | None = None
        self.safety_governance_valid = False
        self.safety_audit_valid = False
        self.safety_security_clear = False
        self.safety_runtime_stable = False
        self.safety_dependencies_complete = False
        self.safety_execution_consistent = False
        self.safety_workflow_integrity = False
        self.safety_continuation_allowed = False
        self.safety_human_review_required = False
        self.safety_sentinel_escalation_required = False
        self.safety_centinela_escalation_required = False
        self.safety_autonomy_limited = False
        self.safety_context_preserved = False
        self.safety_traceability_preserved = False
        self.safety_detected_risks: list[str] = []
        self.safety_warnings: list[str] = []
        self.safety_security_events: list[dict] = []
        self.safety_continuation_logs: list[dict] = []
        self.safety_execution_context: dict = {}
        self.safety_governance_history: list[dict] = []
        self.safety_audit_history: list[dict] = []
        self.safety_workflow_history: list[dict] = []
        self.safety_lifecycle: list[dict] = []
        self.continuation_safety_duration_ms = 0
        self.continuation_safety_reasons: list[str] = []
        self.continuation_safety_last_error: str | None = None
        self.continuation_safety_metadata: dict = {}
        self.last_operational_memory_at: datetime | None = None
        self.operational_memory_iteration = 0
        self.operational_memory_status = "stopped"
        self.memories_captured = 0
        self.memories_retrieved = 0
        self.memories_blocked = 0
        self.operational_memory_errors = 0
        self.last_memory_id: str | None = None
        self.memory_execution_id: str | None = None
        self.memory_task_id: str | None = None
        self.memory_type: str | None = None
        self.memory_workflow: str | None = None
        self.memory_event_type: str | None = None
        self.memory_governance_status: str | None = None
        self.memory_audit_status: str | None = None
        self.memory_risk_level: str | None = None
        self.memory_context: dict = {}
        self.memory_record: dict = {}
        self.memory_records: list[dict] = []
        self.memory_reusable_context: dict = {}
        self.memory_integrity_valid = False
        self.memory_context_safe = False
        self.memory_governance_safe = False
        self.memory_traceability_preserved = False
        self.memory_reuse_allowed = False
        self.memory_critical_preserved = False
        self.memory_matched_records = 0
        self.memory_corrupt_records = 0
        self.memory_errors: list[str] = []
        self.memory_warnings: list[str] = []
        self.memory_governance_history: list[dict] = []
        self.memory_audit_history: list[dict] = []
        self.memory_workflow_history: list[dict] = []
        self.memory_continuation_history: list[dict] = []
        self.memory_lifecycle: list[dict] = []
        self.operational_memory_duration_ms = 0
        self.operational_memory_reasons: list[str] = []
        self.operational_memory_last_error: str | None = None
        self.operational_memory_metadata: dict = {}
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

    def mark_prompt_execution_result(self, result: dict) -> None:
        self.last_prompt_execution_at = datetime.now(timezone.utc)
        self.prompt_execution_iteration += 1
        self.prompt_execution_status = result.get("status") or "unknown"
        self.prompt_execution_prompt_status = result.get("prompt_status")
        self.last_prompt_execution_id = result.get("prompt_execution_id")
        self.prompt_execution_type = result.get("prompt_type")
        self.prompt_execution_objective = result.get("objective")
        self.prompt_execution_provider = result.get("provider_name")
        self.prompt_execution_provider_session_id = result.get(
            "provider_session_id"
        )
        self.prompt_execution_request_id = result.get("request_id")
        self.prompt_execution_execution_id = result.get("execution_id")
        self.prompt_execution_task_id = result.get("task_id")
        self.prompt_execution_prompt_size_bytes = max(
            0,
            int(result.get("prompt_size_bytes") or 0),
        )
        self.prompt_execution_output_available = bool(
            result.get("output_available")
        )
        self.prompt_execution_output_size_bytes = max(
            0,
            int(result.get("output_size_bytes") or 0),
        )
        self.prompt_execution_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.prompt_execution_provider_duration_ms = max(
            0,
            int(result.get("provider_duration_ms") or 0),
        )
        self.prompt_execution_usage = dict(result.get("usage") or {})
        self.prompt_execution_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.prompt_execution_last_error = result.get("error")
        self.prompt_execution_lifecycle = [
            dict(entry)
            for entry in (result.get("lifecycle") or [])
            if isinstance(entry, dict)
        ]
        if self.prompt_execution_status == "completed":
            self.prompt_executions_completed += 1
        elif self.prompt_execution_status == "rejected":
            self.prompt_executions_rejected += 1
        else:
            self.prompt_executions_failed += 1

    def mark_provider_response_handling_result(self, result: dict) -> None:
        self.last_provider_response_handling_at = datetime.now(timezone.utc)
        self.provider_response_handling_iteration += 1
        self.provider_response_handling_status = result.get("status") or "unknown"
        self.provider_response_status = result.get("response_status")
        self.provider_response_type = result.get("response_type")
        self.last_provider_response_handling_id = result.get("handling_id")
        self.last_provider_response_id = result.get("response_id")
        self.provider_response_provider_id = result.get("provider_id")
        self.provider_response_request_id = result.get("provider_request_id")
        self.provider_response_execution_id = result.get("execution_id")
        self.provider_response_task_id = result.get("task_id")
        self.provider_response_validation_status = result.get("validation_status")
        self.provider_response_audit_status = (
            result.get("audit_status") or "not_ready"
        )
        self.provider_response_output_available = bool(
            result.get("output_available")
        )
        self.provider_response_output_size_bytes = max(
            0,
            int(result.get("output_size_bytes") or 0),
        )
        self.provider_response_storage_prepared = bool(
            result.get("storage_prepared")
        )
        self.provider_response_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.provider_response_audit_package = dict(
            result.get("audit_package") or {}
        )
        self.provider_response_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.provider_response_last_error = result.get("error")
        self.provider_response_lifecycle = [
            dict(entry)
            for entry in (result.get("lifecycle") or [])
            if isinstance(entry, dict)
        ]
        if self.provider_response_handling_status == "handled":
            self.provider_responses_handled += 1
        elif self.provider_response_handling_status == "rejected":
            self.provider_responses_rejected += 1
        else:
            self.provider_responses_failed += 1

    def mark_provider_failure_control_result(self, result: dict) -> None:
        self.last_provider_failure_control_at = datetime.now(timezone.utc)
        self.provider_failure_control_iteration += 1
        self.provider_failure_control_status = result.get("status") or "unknown"
        self.provider_failure_detected = bool(result.get("failure_detected"))
        self.last_provider_failure_id = result.get("failure_id")
        self.provider_failure_provider_id = result.get("provider_id")
        self.provider_failure_execution_id = result.get("execution_id")
        self.provider_failure_task_id = result.get("task_id")
        self.provider_failure_request_id = result.get("provider_request_id")
        self.provider_failure_session_id = result.get("provider_session_id")
        self.provider_failure_type = result.get("failure_type")
        self.provider_failure_severity = result.get("failure_severity")
        self.provider_failure_state = result.get("failure_status")
        self.provider_failure_recovery_status = (
            result.get("recovery_status") or "not_required"
        )
        self.provider_failure_runtime_state = result.get("runtime_state")
        self.provider_failure_execution_impact = (
            result.get("execution_impact") or "none"
        )
        self.provider_failure_continuation_blocked = bool(
            result.get("continuation_blocked")
        )
        self.provider_failure_context_preserved = bool(
            result.get("context_preserved")
        )
        self.provider_failure_recovery_prepared = bool(
            result.get("recovery_prepared")
        )
        self.provider_failure_escalation_required = bool(
            result.get("escalation_required")
        )
        self.provider_failure_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.provider_failure_timestamps = dict(result.get("timestamps") or {})
        self.provider_failure_lifecycle = [
            dict(entry)
            for entry in (result.get("lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.provider_failure_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.provider_failure_last_error = result.get("error")
        self.provider_failure_metadata = dict(result.get("metadata") or {})
        if self.provider_failure_detected:
            self.provider_failures_detected += 1
            if self.provider_failure_state in {
                "contained",
                "blocked",
                "recovery_pending",
            }:
                self.provider_failures_contained += 1
            if self.provider_failure_continuation_blocked:
                self.provider_failures_blocked += 1
            if self.provider_failure_escalation_required:
                self.provider_failures_escalated += 1
        if self.provider_failure_control_status == "error":
            self.provider_failure_control_errors += 1

    def mark_provider_routing_result(self, result: dict) -> None:
        self.last_provider_routing_at = datetime.now(timezone.utc)
        self.provider_routing_iteration += 1
        self.provider_routing_status = result.get("status") or "unknown"
        self.last_provider_routing_id = result.get("routing_id")
        self.provider_routing_type = result.get("routing_type")
        self.provider_routing_task_type = result.get("task_type")
        self.provider_routing_selected_provider = result.get(
            "provider_selected"
        )
        self.provider_routing_cost_estimate = result.get("cost_estimate")
        self.provider_routing_execution_priority = result.get(
            "execution_priority"
        )
        self.provider_routing_reason = result.get("routing_reason")
        self.provider_routing_fallback_status = result.get("fallback_status")
        self.provider_routing_fallback_provider = result.get(
            "fallback_provider"
        )
        self.provider_routing_provider_degraded = bool(
            result.get("provider_degraded")
        )
        self.provider_routing_quality_estimate = result.get("quality_estimate")
        self.provider_routing_execution_mode = result.get("execution_mode")
        self.provider_routing_runtime_limits = dict(
            result.get("runtime_limits") or {}
        )
        self.provider_routing_available_providers = [
            str(provider)
            for provider in (result.get("available_providers") or [])
        ]
        self.provider_routing_blocked_providers = [
            str(provider)
            for provider in (result.get("blocked_providers") or [])
        ]
        self.provider_routing_evaluated_providers = [
            dict(provider)
            for provider in (result.get("evaluated_providers") or [])
            if isinstance(provider, dict)
        ]
        self.provider_routing_selected_health = dict(
            result.get("selected_provider_health") or {}
        )
        self.provider_routing_fallback_health = dict(
            result.get("fallback_health") or {}
        )
        self.provider_routing_conflict = bool(result.get("routing_conflict"))
        self.provider_routing_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.provider_routing_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.provider_routing_last_error = result.get("error")
        self.provider_routing_metadata = dict(result.get("metadata") or {})
        if self.provider_routing_status == "selected":
            self.provider_routes_selected += 1
        elif self.provider_routing_status == "degraded":
            self.provider_routes_degraded += 1
            self.provider_routes_selected += 1
        elif self.provider_routing_status == "blocked":
            self.provider_routes_blocked += 1
        else:
            self.provider_routing_errors += 1

    def mark_self_validation_result(self, result: dict) -> None:
        self.last_self_validation_at = datetime.now(timezone.utc)
        self.self_validation_iteration += 1
        self.self_validation_status = result.get("validation_status") or (
            result.get("status") or "unknown"
        )
        self.last_self_validation_id = result.get("validation_id")
        self.self_validation_execution_id = result.get("execution_id")
        self.self_validation_task_id = result.get("task_id")
        self.self_validation_risk_status = result.get("risk_status")
        self.self_validation_audit_required = bool(result.get("audit_required"))
        self.self_validation_self_approved = bool(result.get("self_approved"))
        self.self_validation_continuation_blocked = bool(
            result.get("continuation_blocked")
        )
        self.self_validation_runtime_protected = bool(
            result.get("runtime_protected")
        )
        self.self_validation_modified_files = [
            str(path) for path in (result.get("modified_files") or [])
        ]
        self.self_validation_logs = [
            dict(log)
            for log in (result.get("validation_logs") or [])
            if isinstance(log, dict)
        ]
        self.self_validation_detected_risks = [
            str(risk) for risk in (result.get("detected_risks") or [])
        ]
        self.self_validation_inconsistencies = [
            str(item) for item in (result.get("inconsistencies") or [])
        ]
        self.self_validation_audit_package = dict(
            result.get("audit_package") or {}
        )
        self.self_validation_output_count = max(
            0,
            int(result.get("output_count") or 0),
        )
        self.self_validation_response_count = max(
            0,
            int(result.get("response_count") or 0),
        )
        self.self_validation_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.self_validation_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.self_validation_last_error = result.get("error")
        self.self_validation_metadata = dict(result.get("metadata") or {})
        if self.self_validation_status == "valid":
            self.self_validations_valid += 1
        elif self.self_validation_status == "warning":
            self.self_validations_warning += 1
        elif self.self_validation_status == "invalid":
            self.self_validations_invalid += 1
        else:
            self.self_validation_errors += 1

    def mark_audit_request_result(self, result: dict) -> None:
        self.last_audit_request_at = datetime.now(timezone.utc)
        self.audit_request_iteration += 1
        self.audit_request_status = result.get("status") or "unknown"
        self.last_audit_request_id = result.get("audit_id")
        self.audit_request_execution_id = result.get("execution_id")
        self.audit_request_task_id = result.get("task_id")
        self.audit_request_type = result.get("audit_type")
        self.audit_request_audit_status = result.get("audit_status")
        self.audit_request_validation_status = result.get("validation_status")
        self.audit_request_risk_status = result.get("risk_status")
        self.audit_request_package = dict(result.get("audit_package") or {})
        self.audit_request_package_hash = result.get("audit_package_hash")
        self.audit_request_continuation_frozen = bool(
            result.get("continuation_frozen")
        )
        self.audit_request_continuation_status = result.get(
            "continuation_status"
        )
        self.audit_request_traceability_preserved = bool(
            result.get("traceability_preserved")
        )
        self.audit_request_delivery_targets = [
            str(target) for target in (result.get("delivery_targets") or [])
        ]
        self.audit_request_delivery_status = result.get("delivery_status")
        self.audit_request_lifecycle = [
            dict(entry)
            for entry in (result.get("audit_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.audit_request_modified_files = [
            str(path) for path in (result.get("modified_files") or [])
        ]
        self.audit_request_detected_risks = [
            str(risk) for risk in (result.get("detected_risks") or [])
        ]
        self.audit_request_provider_context = dict(
            result.get("provider_context") or {}
        )
        self.audit_request_runtime_state = dict(result.get("runtime_state") or {})
        self.audit_request_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.audit_request_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.audit_request_last_error = result.get("error")
        self.audit_request_metadata = dict(result.get("metadata") or {})
        if self.audit_request_status == "pending":
            self.audit_requests_pending += 1
        elif self.audit_request_status == "blocked":
            self.audit_requests_blocked += 1
        else:
            self.audit_request_errors += 1

    def mark_audit_response_result(self, result: dict) -> None:
        self.last_audit_response_at = datetime.now(timezone.utc)
        self.audit_response_iteration += 1
        self.audit_response_status = result.get("status") or "unknown"
        self.last_audit_response_id = result.get("response_id")
        self.audit_response_audit_id = result.get("audit_id")
        self.audit_response_execution_id = result.get("execution_id")
        self.audit_response_task_id = result.get("task_id")
        self.audit_response_result = result.get("audit_result")
        self.audit_response_risk_level = result.get("risk_level")
        self.audit_response_correction_status = result.get("correction_status")
        self.audit_response_continuation_status = result.get(
            "continuation_status"
        )
        self.audit_response_human_approval_status = result.get(
            "human_approval_status"
        )
        self.audit_response_security_escalation_status = result.get(
            "security_escalation_status"
        )
        self.audit_response_centinela_escalation = bool(
            result.get("centinela_escalation")
        )
        self.audit_response_execution_decision = result.get("execution_decision")
        self.audit_response_context_preserved = bool(
            result.get("context_preserved")
        )
        self.audit_response_integrity_preserved = bool(
            result.get("audit_integrity_preserved")
        )
        self.audit_response_warnings = [
            str(warning) for warning in (result.get("warnings") or [])
        ]
        self.audit_response_detected_risks = [
            str(risk) for risk in (result.get("detected_risks") or [])
        ]
        self.audit_response_rejection_reasons = [
            str(reason) for reason in (result.get("rejection_reasons") or [])
        ]
        self.audit_response_correction_requirements = [
            str(item)
            for item in (result.get("correction_requirements") or [])
        ]
        self.audit_response_modified_files = [
            str(path) for path in (result.get("modified_files") or [])
        ]
        self.audit_response_logs = [
            dict(entry)
            for entry in (result.get("audit_logs") or [])
            if isinstance(entry, dict)
        ]
        self.audit_response_lifecycle = [
            dict(entry)
            for entry in (result.get("audit_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.audit_response_execution_context = dict(
            result.get("execution_context") or {}
        )
        self.audit_response_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.audit_response_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.audit_response_last_error = result.get("error")
        self.audit_response_metadata = dict(result.get("metadata") or {})

        if self.audit_response_status == "approved":
            self.audit_responses_approved += 1
        elif self.audit_response_status == "approved_with_warnings":
            self.audit_responses_warning += 1
        elif self.audit_response_status == "needs_fix":
            self.audit_responses_needs_fix += 1
        elif self.audit_response_status == "rejected":
            self.audit_responses_rejected += 1
        else:
            self.audit_response_errors += 1

    def mark_approval_gate_result(self, result: dict) -> None:
        self.last_approval_gate_at = datetime.now(timezone.utc)
        self.approval_gate_iteration += 1
        self.approval_gate_status = result.get("status") or "unknown"
        self.last_approval_id = result.get("approval_id")
        self.approval_gate_execution_id = result.get("execution_id")
        self.approval_gate_task_id = result.get("task_id")
        self.approval_gate_type = result.get("approval_type")
        self.approval_gate_approval_status = result.get("approval_status")
        self.approval_gate_audit_status = result.get("audit_status")
        self.approval_gate_human_decision = result.get("human_decision")
        self.approval_gate_continuation_status = result.get(
            "continuation_status"
        )
        self.approval_gate_risk_status = result.get("risk_status")
        self.approval_gate_governance_status = result.get("governance_status")
        self.approval_gate_context_preserved = bool(
            result.get("context_preserved")
        )
        self.approval_gate_human_authority_preserved = bool(
            result.get("human_authority_preserved")
        )
        self.approval_gate_autonomy_blocked = bool(
            result.get("autonomy_blocked", True)
        )
        self.approval_gate_decided_by = result.get("decided_by")
        self.approval_gate_decision_reason = str(
            result.get("decision_reason") or ""
        )
        self.approval_gate_human_report = dict(result.get("human_report") or {})
        self.approval_gate_modified_files = [
            str(path) for path in (result.get("modified_files") or [])
        ]
        self.approval_gate_detected_risks = [
            str(risk) for risk in (result.get("detected_risks") or [])
        ]
        self.approval_gate_warnings = [
            str(warning) for warning in (result.get("warnings") or [])
        ]
        self.approval_gate_lifecycle = [
            dict(entry)
            for entry in (result.get("approval_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.approval_gate_execution_context = dict(
            result.get("execution_context") or {}
        )
        self.approval_gate_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.approval_gate_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.approval_gate_last_error = result.get("error")
        self.approval_gate_metadata = dict(result.get("metadata") or {})

        if self.approval_gate_status == "pending":
            self.approval_requests_pending += 1
        elif self.approval_gate_status == "approved":
            self.approval_decisions_approved += 1
        elif self.approval_gate_status == "rejected":
            self.approval_decisions_rejected += 1
        elif self.approval_gate_status == "needs_changes":
            self.approval_decisions_needs_changes += 1
        elif self.approval_gate_status == "escalated":
            self.approval_decisions_escalated += 1
        else:
            self.approval_gate_errors += 1

    def mark_execution_blocking_result(self, result: dict) -> None:
        self.last_execution_blocking_at = datetime.now(timezone.utc)
        self.execution_blocking_iteration += 1
        self.execution_blocking_status = result.get("status") or "unknown"
        self.last_execution_block_id = result.get("block_id")
        self.execution_block_execution_id = result.get("execution_id")
        self.execution_block_task_id = result.get("task_id")
        self.execution_block_type = result.get("block_type")
        self.execution_block_status = result.get("block_status")
        self.execution_block_classification = result.get("block_classification")
        self.execution_block_reason = result.get("block_reason")
        self.execution_block_risk_level = result.get("risk_level")
        self.execution_block_escalation_status = result.get("escalation_status")
        self.execution_block_continuation_status = result.get(
            "continuation_status"
        )
        self.execution_block_execution_frozen = bool(
            result.get("execution_frozen")
        )
        self.execution_block_continuation_blocked = bool(
            result.get("continuation_blocked")
        )
        self.execution_block_context_preserved = bool(
            result.get("context_preserved")
        )
        self.execution_block_governance_protected = bool(
            result.get("governance_protected")
        )
        self.execution_block_security_authority_required = bool(
            result.get("security_authority_required")
        )
        self.execution_block_human_authority_required = bool(
            result.get("human_authority_required")
        )
        self.execution_block_modified_files = [
            str(path) for path in (result.get("modified_files") or [])
        ]
        self.execution_block_runtime_logs = [
            dict(entry)
            for entry in (result.get("runtime_logs") or [])
            if isinstance(entry, dict)
        ]
        self.execution_block_audit_history = [
            dict(entry)
            for entry in (result.get("audit_history") or [])
            if isinstance(entry, dict)
        ]
        self.execution_block_risk_history = [
            str(risk) for risk in (result.get("risk_history") or [])
        ]
        self.execution_block_runtime_state = dict(
            result.get("runtime_state") or {}
        )
        self.execution_block_provider_context = dict(
            result.get("provider_context") or {}
        )
        self.execution_block_execution_context = dict(
            result.get("execution_context") or {}
        )
        self.execution_block_lifecycle = [
            dict(entry)
            for entry in (result.get("blocking_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.execution_block_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.execution_block_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.execution_block_last_error = result.get("error")
        self.execution_block_metadata = dict(result.get("metadata") or {})

        if self.execution_blocking_status == "active":
            self.execution_blocks_active += 1
        elif self.execution_blocking_status == "blocked":
            self.execution_blocks_invalid += 1
        else:
            self.execution_blocking_errors += 1

    def mark_phase_continuation_result(self, result: dict) -> None:
        self.last_phase_continuation_at = datetime.now(timezone.utc)
        self.phase_continuation_iteration += 1
        self.phase_continuation_status = result.get("status") or "unknown"
        self.last_phase_continuation_id = result.get("continuation_id")
        self.phase_continuation_current_phase = result.get("current_phase")
        self.phase_continuation_current_subphase = result.get("current_subphase")
        self.phase_continuation_next_subphase = result.get("next_subphase")
        self.phase_continuation_type = result.get("continuation_type")
        self.phase_continuation_governance_status = result.get(
            "governance_status"
        )
        self.phase_continuation_audit_status = result.get("audit_status")
        self.phase_continuation_execution_status = result.get("execution_status")
        self.phase_continuation_runtime_status = result.get(
            "continuation_status"
        )
        self.phase_continuation_roadmap_loaded = bool(
            result.get("roadmap_loaded")
        )
        self.phase_continuation_dependencies_satisfied = bool(
            result.get("dependencies_satisfied")
        )
        self.phase_continuation_governance_satisfied = bool(
            result.get("governance_satisfied")
        )
        self.phase_continuation_audit_satisfied = bool(
            result.get("audit_satisfied")
        )
        self.phase_continuation_execution_stable = bool(
            result.get("execution_stable")
        )
        self.phase_continuation_runtime_safe = bool(result.get("runtime_safe"))
        self.phase_continuation_context_preserved = bool(
            result.get("context_preserved")
        )
        self.phase_continuation_traceability_preserved = bool(
            result.get("traceability_preserved")
        )
        self.phase_continuation_progression_allowed = bool(
            result.get("progression_allowed")
        )
        self.phase_continuation_roadmap = [
            str(item) for item in (result.get("roadmap") or [])
        ]
        self.phase_continuation_completed_subphases = [
            str(item) for item in (result.get("completed_subphases") or [])
        ]
        self.phase_continuation_required_dependencies = [
            str(item) for item in (result.get("required_dependencies") or [])
        ]
        self.phase_continuation_missing_dependencies = [
            str(item) for item in (result.get("missing_dependencies") or [])
        ]
        self.phase_continuation_execution_context = dict(
            result.get("execution_context") or {}
        )
        self.phase_continuation_lifecycle_history = [
            dict(entry)
            for entry in (result.get("lifecycle_history") or [])
            if isinstance(entry, dict)
        ]
        self.phase_continuation_audit_history = [
            dict(entry)
            for entry in (result.get("audit_history") or [])
            if isinstance(entry, dict)
        ]
        self.phase_continuation_governance_history = [
            dict(entry)
            for entry in (result.get("governance_history") or [])
            if isinstance(entry, dict)
        ]
        self.phase_continuation_lifecycle = [
            dict(entry)
            for entry in (result.get("continuation_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.phase_continuation_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.phase_continuation_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.phase_continuation_last_error = result.get("error")
        self.phase_continuation_metadata = dict(result.get("metadata") or {})

        if self.phase_continuation_status == "ready":
            self.phase_continuations_ready += 1
        elif self.phase_continuation_status == "blocked":
            self.phase_continuations_blocked += 1
        elif self.phase_continuation_status == "completed":
            self.phase_continuations_completed += 1
        else:
            self.phase_continuation_errors += 1

    def mark_checkpoint_recovery_result(self, result: dict) -> None:
        self.last_checkpoint_recovery_at = datetime.now(timezone.utc)
        self.checkpoint_recovery_iteration += 1
        self.checkpoint_recovery_status = result.get("status") or "unknown"
        self.last_checkpoint_id = result.get("checkpoint_id")
        self.last_recovery_id = result.get("recovery_id")
        self.checkpoint_execution_id = result.get("execution_id")
        self.checkpoint_task_id = result.get("task_id")
        self.checkpoint_type = result.get("checkpoint_type")
        self.checkpoint_recovery_state = result.get("recovery_status")
        self.checkpoint_valid = bool(result.get("checkpoint_valid"))
        self.checkpoint_checksum = result.get("checkpoint_checksum")
        self.checkpoint_restoration_ready = bool(result.get("restoration_ready"))
        self.checkpoint_continuation_status = result.get("continuation_status")
        self.checkpoint_context_preserved = bool(result.get("context_preserved"))
        self.checkpoint_traceability_preserved = bool(
            result.get("traceability_preserved")
        )
        self.checkpoint_governance_review_required = bool(
            result.get("governance_review_required")
        )
        self.checkpoint_audit_review_required = bool(
            result.get("audit_review_required")
        )
        self.checkpoint_payload = dict(result.get("checkpoint") or {})
        self.checkpoint_restored_state = dict(result.get("restored_state") or {})
        self.checkpoint_phase_state = dict(result.get("phase_state") or {})
        self.checkpoint_runtime_state = dict(result.get("runtime_state") or {})
        self.checkpoint_governance_state = dict(
            result.get("governance_state") or {}
        )
        self.checkpoint_audit_state = dict(result.get("audit_state") or {})
        self.checkpoint_provider_state = dict(result.get("provider_state") or {})
        self.checkpoint_execution_context = dict(
            result.get("execution_context") or {}
        )
        self.checkpoint_lifecycle_state = dict(
            result.get("lifecycle_state") or {}
        )
        self.checkpoint_modified_files = [
            str(path) for path in (result.get("modified_files") or [])
        ]
        self.checkpoint_recovery_logs = [
            dict(entry)
            for entry in (result.get("recovery_logs") or [])
            if isinstance(entry, dict)
        ]
        self.checkpoint_recovery_lifecycle = [
            dict(entry)
            for entry in (result.get("recovery_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.checkpoint_recovery_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.checkpoint_recovery_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.checkpoint_recovery_last_error = result.get("error")
        self.checkpoint_recovery_metadata = dict(result.get("metadata") or {})

        if self.checkpoint_recovery_status == "created":
            self.checkpoints_created += 1
        elif self.checkpoint_recovery_status == "recovery_prepared":
            self.checkpoint_recoveries_prepared += 1
        elif self.checkpoint_recovery_status == "blocked":
            self.checkpoint_recoveries_blocked += 1
        else:
            self.checkpoint_recovery_errors += 1

    def mark_execution_resume_result(self, result: dict) -> None:
        self.last_execution_resume_at = datetime.now(timezone.utc)
        self.execution_resume_iteration += 1
        self.execution_resume_status = result.get("status") or "unknown"
        self.last_resume_id = result.get("resume_id")
        self.resume_execution_id = result.get("execution_id")
        self.resume_task_id = result.get("task_id")
        self.resume_checkpoint_id = result.get("checkpoint_id")
        self.resume_type = result.get("resume_type")
        self.resume_governance_status = result.get("governance_status")
        self.resume_audit_status = result.get("audit_status")
        self.resume_state = result.get("resume_status")
        self.resume_continuation_status = result.get("continuation_status")
        self.resume_runtime_stable = bool(result.get("runtime_stable"))
        self.resume_checkpoint_valid = bool(result.get("checkpoint_valid"))
        self.resume_execution_consistent = bool(
            result.get("execution_consistent")
        )
        self.resume_governance_satisfied = bool(
            result.get("governance_satisfied")
        )
        self.resume_audit_satisfied = bool(result.get("audit_satisfied"))
        self.resume_workflow_continuity_preserved = bool(
            result.get("workflow_continuity_preserved")
        )
        self.resume_execution_reactivated = bool(
            result.get("execution_reactivated")
        )
        self.resume_context_restored = bool(result.get("context_restored"))
        self.resume_context_preserved = bool(result.get("context_preserved"))
        self.resume_traceability_preserved = bool(
            result.get("traceability_preserved")
        )
        self.resume_provider_context_restored = bool(
            result.get("provider_context_restored")
        )
        self.resume_restored_state = dict(result.get("restored_state") or {})
        self.resume_execution_context = dict(
            result.get("execution_context") or {}
        )
        self.resume_lifecycle_state = dict(result.get("lifecycle_state") or {})
        self.resume_runtime_state = dict(result.get("runtime_state") or {})
        self.resume_governance_state = dict(result.get("governance_state") or {})
        self.resume_audit_state = dict(result.get("audit_state") or {})
        self.resume_provider_state = dict(result.get("provider_state") or {})
        self.resume_lifecycle_history = [
            dict(entry)
            for entry in (result.get("lifecycle_history") or [])
            if isinstance(entry, dict)
        ]
        self.resume_audit_history = [
            dict(entry)
            for entry in (result.get("audit_history") or [])
            if isinstance(entry, dict)
        ]
        self.resume_governance_history = [
            dict(entry)
            for entry in (result.get("governance_history") or [])
            if isinstance(entry, dict)
        ]
        self.resume_recovery_history = [
            dict(entry)
            for entry in (result.get("recovery_history") or [])
            if isinstance(entry, dict)
        ]
        self.resume_modified_files = [
            str(path) for path in (result.get("modified_files") or [])
        ]
        self.resume_lifecycle = [
            dict(entry)
            for entry in (result.get("resume_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.execution_resume_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.execution_resume_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.execution_resume_last_error = result.get("error")
        self.execution_resume_metadata = dict(result.get("metadata") or {})

        if self.execution_resume_status == "resumed":
            self.execution_resumes_completed += 1
        elif self.execution_resume_status == "blocked":
            self.execution_resumes_blocked += 1
        else:
            self.execution_resume_errors += 1

    def mark_workflow_chaining_result(self, result: dict) -> None:
        self.last_workflow_chaining_at = datetime.now(timezone.utc)
        self.workflow_chaining_iteration += 1
        self.workflow_chaining_status = result.get("status") or "unknown"
        self.last_chaining_id = result.get("chaining_id")
        self.chaining_current_workflow = result.get("current_workflow")
        self.chaining_next_workflow = result.get("next_workflow")
        self.chaining_current_phase = result.get("current_phase")
        self.chaining_current_subphase = result.get("current_subphase")
        self.chaining_type = result.get("chaining_type")
        self.chaining_governance_status = result.get("governance_status")
        self.chaining_audit_status = result.get("audit_status")
        self.chaining_execution_status = result.get("execution_status")
        self.chaining_dependency_status = result.get("dependency_status")
        self.chaining_continuation_status = result.get("continuation_status")
        self.chaining_roadmap_loaded = bool(result.get("roadmap_loaded"))
        self.chaining_current_workflow_completed = bool(
            result.get("current_workflow_completed")
        )
        self.chaining_dependencies_satisfied = bool(
            result.get("dependencies_satisfied")
        )
        self.chaining_governance_satisfied = bool(
            result.get("governance_satisfied")
        )
        self.chaining_audit_satisfied = bool(result.get("audit_satisfied"))
        self.chaining_execution_stable = bool(result.get("execution_stable"))
        self.chaining_runtime_safe = bool(result.get("runtime_safe"))
        self.chaining_progression_allowed = bool(
            result.get("progression_allowed")
        )
        self.chaining_workflow_activation = bool(
            result.get("workflow_activation")
        )
        self.chaining_context_preserved = bool(result.get("context_preserved"))
        self.chaining_traceability_preserved = bool(
            result.get("traceability_preserved")
        )
        self.chaining_roadmap = [
            str(item) for item in (result.get("roadmap") or [])
        ]
        self.chaining_completed_workflows = [
            str(item) for item in (result.get("completed_workflows") or [])
        ]
        self.chaining_required_dependencies = [
            str(item) for item in (result.get("required_dependencies") or [])
        ]
        self.chaining_missing_dependencies = [
            str(item) for item in (result.get("missing_dependencies") or [])
        ]
        self.chaining_next_workflow_context = dict(
            result.get("next_workflow_context") or {}
        )
        self.chaining_execution_context = dict(
            result.get("execution_context") or {}
        )
        self.chaining_lifecycle_history = [
            dict(entry)
            for entry in (result.get("lifecycle_history") or [])
            if isinstance(entry, dict)
        ]
        self.chaining_roadmap_history = [
            dict(entry)
            for entry in (result.get("roadmap_history") or [])
            if isinstance(entry, dict)
        ]
        self.chaining_governance_history = [
            dict(entry)
            for entry in (result.get("governance_history") or [])
            if isinstance(entry, dict)
        ]
        self.chaining_audit_history = [
            dict(entry)
            for entry in (result.get("audit_history") or [])
            if isinstance(entry, dict)
        ]
        self.chaining_lifecycle = [
            dict(entry)
            for entry in (result.get("chaining_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.workflow_chaining_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.workflow_chaining_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.workflow_chaining_last_error = result.get("error")
        self.workflow_chaining_metadata = dict(result.get("metadata") or {})

        if self.workflow_chaining_status == "activated":
            self.workflow_chains_activated += 1
        elif self.workflow_chaining_status == "blocked":
            self.workflow_chains_blocked += 1
        elif self.workflow_chaining_status == "completed":
            self.workflow_chains_completed += 1
        else:
            self.workflow_chaining_errors += 1

    def mark_continuation_safety_result(self, result: dict) -> None:
        self.last_continuation_safety_at = datetime.now(timezone.utc)
        self.continuation_safety_iteration += 1
        self.continuation_safety_status = result.get("status") or "unknown"
        self.last_safety_id = result.get("safety_id")
        self.safety_execution_id = result.get("execution_id")
        self.safety_task_id = result.get("task_id")
        self.safety_type = result.get("safety_type")
        self.safety_current_workflow = result.get("current_workflow")
        self.safety_next_workflow = result.get("next_workflow")
        self.safety_continuation_status = result.get("continuation_status")
        self.safety_governance_status = result.get("governance_status")
        self.safety_audit_status = result.get("audit_status")
        self.safety_security_status = result.get("security_status")
        self.safety_risk_level = result.get("risk_level")
        self.safety_governance_valid = bool(result.get("governance_valid"))
        self.safety_audit_valid = bool(result.get("audit_valid"))
        self.safety_security_clear = bool(result.get("security_clear"))
        self.safety_runtime_stable = bool(result.get("runtime_stable"))
        self.safety_dependencies_complete = bool(
            result.get("dependencies_complete")
        )
        self.safety_execution_consistent = bool(
            result.get("execution_consistent")
        )
        self.safety_workflow_integrity = bool(result.get("workflow_integrity"))
        self.safety_continuation_allowed = bool(
            result.get("continuation_allowed")
        )
        self.safety_human_review_required = bool(
            result.get("human_review_required")
        )
        self.safety_sentinel_escalation_required = bool(
            result.get("sentinel_escalation_required")
        )
        self.safety_centinela_escalation_required = bool(
            result.get("centinela_escalation_required")
        )
        self.safety_autonomy_limited = bool(result.get("autonomy_limited"))
        self.safety_context_preserved = bool(result.get("context_preserved"))
        self.safety_traceability_preserved = bool(
            result.get("traceability_preserved")
        )
        self.safety_detected_risks = [
            str(item) for item in (result.get("detected_risks") or [])
        ]
        self.safety_warnings = [
            str(item) for item in (result.get("warnings") or [])
        ]
        self.safety_security_events = [
            dict(entry)
            for entry in (result.get("security_events") or [])
            if isinstance(entry, dict)
        ]
        self.safety_continuation_logs = [
            dict(entry)
            for entry in (result.get("continuation_logs") or [])
            if isinstance(entry, dict)
        ]
        self.safety_execution_context = dict(
            result.get("execution_context") or {}
        )
        self.safety_governance_history = [
            dict(entry)
            for entry in (result.get("governance_history") or [])
            if isinstance(entry, dict)
        ]
        self.safety_audit_history = [
            dict(entry)
            for entry in (result.get("audit_history") or [])
            if isinstance(entry, dict)
        ]
        self.safety_workflow_history = [
            dict(entry)
            for entry in (result.get("workflow_history") or [])
            if isinstance(entry, dict)
        ]
        self.safety_lifecycle = [
            dict(entry)
            for entry in (result.get("safety_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.continuation_safety_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.continuation_safety_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.continuation_safety_last_error = result.get("error")
        self.continuation_safety_metadata = dict(result.get("metadata") or {})

        if self.continuation_safety_status == "safe_continuation":
            self.continuations_safe += 1
        elif self.continuation_safety_status == "warning_continuation":
            self.continuations_warning += 1
        elif self.continuation_safety_status == "blocked_continuation":
            self.continuations_blocked += 1
        elif self.continuation_safety_status == "critical_continuation":
            self.continuations_critical += 1
        else:
            self.continuation_safety_errors += 1

    def mark_operational_memory_result(self, result: dict) -> None:
        self.last_operational_memory_at = datetime.now(timezone.utc)
        self.operational_memory_iteration += 1
        self.operational_memory_status = result.get("status") or "unknown"
        self.last_memory_id = result.get("memory_id")
        self.memory_execution_id = result.get("execution_id")
        self.memory_task_id = result.get("task_id")
        self.memory_type = result.get("memory_type")
        self.memory_workflow = result.get("workflow")
        self.memory_event_type = result.get("event_type")
        self.memory_governance_status = result.get("governance_status")
        self.memory_audit_status = result.get("audit_status")
        self.memory_risk_level = result.get("risk_level")
        self.memory_context = dict(result.get("memory_context") or {})
        self.memory_record = dict(result.get("memory_record") or {})
        self.memory_records = [
            dict(record)
            for record in (result.get("memory_records") or [])
            if isinstance(record, dict)
        ]
        self.memory_reusable_context = dict(
            result.get("reusable_context") or {}
        )
        self.memory_integrity_valid = bool(result.get("integrity_valid"))
        self.memory_context_safe = bool(result.get("context_safe"))
        self.memory_governance_safe = bool(result.get("governance_safe"))
        self.memory_traceability_preserved = bool(
            result.get("traceability_preserved")
        )
        self.memory_reuse_allowed = bool(result.get("reuse_allowed"))
        self.memory_critical_preserved = bool(
            result.get("critical_memory_preserved")
        )
        self.memory_matched_records = max(
            0,
            int(result.get("matched_records") or 0),
        )
        self.memory_corrupt_records = max(
            0,
            int(result.get("corrupt_records") or 0),
        )
        self.memory_errors = [
            str(item) for item in (result.get("errors") or [])
        ]
        self.memory_warnings = [
            str(item) for item in (result.get("warnings") or [])
        ]
        self.memory_governance_history = [
            dict(entry)
            for entry in (result.get("governance_history") or [])
            if isinstance(entry, dict)
        ]
        self.memory_audit_history = [
            dict(entry)
            for entry in (result.get("audit_history") or [])
            if isinstance(entry, dict)
        ]
        self.memory_workflow_history = [
            dict(entry)
            for entry in (result.get("workflow_history") or [])
            if isinstance(entry, dict)
        ]
        self.memory_continuation_history = [
            dict(entry)
            for entry in (result.get("continuation_history") or [])
            if isinstance(entry, dict)
        ]
        self.memory_lifecycle = [
            dict(entry)
            for entry in (result.get("memory_lifecycle") or [])
            if isinstance(entry, dict)
        ]
        self.operational_memory_duration_ms = max(
            0,
            int(result.get("duration_ms") or 0),
        )
        self.operational_memory_reasons = [
            str(reason) for reason in (result.get("reasons") or [])
        ]
        self.operational_memory_last_error = result.get("error")
        self.operational_memory_metadata = dict(result.get("metadata") or {})

        if self.operational_memory_status == "captured":
            self.memories_captured += 1
        elif self.operational_memory_status == "retrieved":
            self.memories_retrieved += 1
        elif self.operational_memory_status == "blocked":
            self.memories_blocked += 1
        else:
            self.operational_memory_errors += 1

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

    def prompt_execution_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_prompt_execution_at": fmt(self.last_prompt_execution_at),
            "prompt_execution_iteration": self.prompt_execution_iteration,
            "prompt_execution_status": self.prompt_execution_status,
            "prompt_status": self.prompt_execution_prompt_status,
            "prompt_executions_completed": self.prompt_executions_completed,
            "prompt_executions_rejected": self.prompt_executions_rejected,
            "prompt_executions_failed": self.prompt_executions_failed,
            "prompt_execution_id": self.last_prompt_execution_id,
            "prompt_type": self.prompt_execution_type,
            "objective": self.prompt_execution_objective,
            "provider_name": self.prompt_execution_provider,
            "provider_session_id": self.prompt_execution_provider_session_id,
            "request_id": self.prompt_execution_request_id,
            "execution_id": self.prompt_execution_execution_id,
            "task_id": self.prompt_execution_task_id,
            "prompt_size_bytes": self.prompt_execution_prompt_size_bytes,
            "output_available": self.prompt_execution_output_available,
            "output_size_bytes": self.prompt_execution_output_size_bytes,
            "duration_ms": self.prompt_execution_duration_ms,
            "provider_duration_ms": self.prompt_execution_provider_duration_ms,
            "usage": dict(self.prompt_execution_usage),
            "reasons": list(self.prompt_execution_reasons),
            "last_error": self.prompt_execution_last_error,
            "lifecycle": [dict(entry) for entry in self.prompt_execution_lifecycle],
        }

    def provider_response_handling_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_provider_response_handling_at": fmt(
                self.last_provider_response_handling_at
            ),
            "provider_response_handling_iteration": (
                self.provider_response_handling_iteration
            ),
            "provider_response_handling_status": (
                self.provider_response_handling_status
            ),
            "response_status": self.provider_response_status,
            "response_type": self.provider_response_type,
            "provider_responses_handled": self.provider_responses_handled,
            "provider_responses_rejected": self.provider_responses_rejected,
            "provider_responses_failed": self.provider_responses_failed,
            "handling_id": self.last_provider_response_handling_id,
            "response_id": self.last_provider_response_id,
            "provider_id": self.provider_response_provider_id,
            "provider_request_id": self.provider_response_request_id,
            "execution_id": self.provider_response_execution_id,
            "task_id": self.provider_response_task_id,
            "validation_status": self.provider_response_validation_status,
            "audit_status": self.provider_response_audit_status,
            "output_available": self.provider_response_output_available,
            "output_size_bytes": self.provider_response_output_size_bytes,
            "storage_prepared": self.provider_response_storage_prepared,
            "duration_ms": self.provider_response_duration_ms,
            "audit_package": dict(self.provider_response_audit_package),
            "reasons": list(self.provider_response_reasons),
            "last_error": self.provider_response_last_error,
            "lifecycle": [dict(entry) for entry in self.provider_response_lifecycle],
        }

    def provider_failure_control_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_provider_failure_control_at": fmt(
                self.last_provider_failure_control_at
            ),
            "provider_failure_control_iteration": (
                self.provider_failure_control_iteration
            ),
            "provider_failure_control_status": (
                self.provider_failure_control_status
            ),
            "failure_detected": self.provider_failure_detected,
            "provider_failures_detected": self.provider_failures_detected,
            "provider_failures_contained": self.provider_failures_contained,
            "provider_failures_blocked": self.provider_failures_blocked,
            "provider_failures_escalated": self.provider_failures_escalated,
            "provider_failure_control_errors": (
                self.provider_failure_control_errors
            ),
            "failure_id": self.last_provider_failure_id,
            "provider_id": self.provider_failure_provider_id,
            "execution_id": self.provider_failure_execution_id,
            "task_id": self.provider_failure_task_id,
            "provider_request_id": self.provider_failure_request_id,
            "provider_session_id": self.provider_failure_session_id,
            "failure_type": self.provider_failure_type,
            "failure_severity": self.provider_failure_severity,
            "failure_status": self.provider_failure_state,
            "recovery_status": self.provider_failure_recovery_status,
            "runtime_state": self.provider_failure_runtime_state,
            "execution_impact": self.provider_failure_execution_impact,
            "continuation_blocked": (
                self.provider_failure_continuation_blocked
            ),
            "context_preserved": self.provider_failure_context_preserved,
            "recovery_prepared": self.provider_failure_recovery_prepared,
            "escalation_required": (
                self.provider_failure_escalation_required
            ),
            "duration_ms": self.provider_failure_duration_ms,
            "timestamps": dict(self.provider_failure_timestamps),
            "lifecycle": [
                dict(entry) for entry in self.provider_failure_lifecycle
            ],
            "reasons": list(self.provider_failure_reasons),
            "last_error": self.provider_failure_last_error,
            "metadata": dict(self.provider_failure_metadata),
        }

    def provider_routing_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_provider_routing_at": fmt(self.last_provider_routing_at),
            "provider_routing_iteration": self.provider_routing_iteration,
            "provider_routing_status": self.provider_routing_status,
            "provider_routes_selected": self.provider_routes_selected,
            "provider_routes_blocked": self.provider_routes_blocked,
            "provider_routes_degraded": self.provider_routes_degraded,
            "provider_routing_errors": self.provider_routing_errors,
            "routing_id": self.last_provider_routing_id,
            "routing_type": self.provider_routing_type,
            "task_type": self.provider_routing_task_type,
            "provider_selected": self.provider_routing_selected_provider,
            "cost_estimate": self.provider_routing_cost_estimate,
            "execution_priority": self.provider_routing_execution_priority,
            "routing_reason": self.provider_routing_reason,
            "fallback_status": self.provider_routing_fallback_status,
            "fallback_provider": self.provider_routing_fallback_provider,
            "provider_degraded": self.provider_routing_provider_degraded,
            "quality_estimate": self.provider_routing_quality_estimate,
            "execution_mode": self.provider_routing_execution_mode,
            "runtime_limits": dict(self.provider_routing_runtime_limits),
            "available_providers": list(
                self.provider_routing_available_providers
            ),
            "blocked_providers": list(self.provider_routing_blocked_providers),
            "evaluated_providers": [
                dict(provider)
                for provider in self.provider_routing_evaluated_providers
            ],
            "selected_provider_health": dict(
                self.provider_routing_selected_health
            ),
            "fallback_health": dict(self.provider_routing_fallback_health),
            "routing_conflict": self.provider_routing_conflict,
            "duration_ms": self.provider_routing_duration_ms,
            "reasons": list(self.provider_routing_reasons),
            "last_error": self.provider_routing_last_error,
            "metadata": dict(self.provider_routing_metadata),
        }

    def self_validation_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_self_validation_at": fmt(self.last_self_validation_at),
            "self_validation_iteration": self.self_validation_iteration,
            "self_validation_status": self.self_validation_status,
            "self_validations_valid": self.self_validations_valid,
            "self_validations_warning": self.self_validations_warning,
            "self_validations_invalid": self.self_validations_invalid,
            "self_validation_errors": self.self_validation_errors,
            "validation_id": self.last_self_validation_id,
            "execution_id": self.self_validation_execution_id,
            "task_id": self.self_validation_task_id,
            "risk_status": self.self_validation_risk_status,
            "audit_required": self.self_validation_audit_required,
            "self_approved": self.self_validation_self_approved,
            "continuation_blocked": (
                self.self_validation_continuation_blocked
            ),
            "runtime_protected": self.self_validation_runtime_protected,
            "modified_files": list(self.self_validation_modified_files),
            "validation_logs": [
                dict(log) for log in self.self_validation_logs
            ],
            "detected_risks": list(self.self_validation_detected_risks),
            "inconsistencies": list(self.self_validation_inconsistencies),
            "audit_package": dict(self.self_validation_audit_package),
            "output_count": self.self_validation_output_count,
            "response_count": self.self_validation_response_count,
            "duration_ms": self.self_validation_duration_ms,
            "reasons": list(self.self_validation_reasons),
            "last_error": self.self_validation_last_error,
            "metadata": dict(self.self_validation_metadata),
        }

    def audit_request_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_audit_request_at": fmt(self.last_audit_request_at),
            "audit_request_iteration": self.audit_request_iteration,
            "audit_request_status": self.audit_request_status,
            "audit_requests_pending": self.audit_requests_pending,
            "audit_requests_blocked": self.audit_requests_blocked,
            "audit_request_errors": self.audit_request_errors,
            "audit_id": self.last_audit_request_id,
            "execution_id": self.audit_request_execution_id,
            "task_id": self.audit_request_task_id,
            "audit_type": self.audit_request_type,
            "audit_status": self.audit_request_audit_status,
            "validation_status": self.audit_request_validation_status,
            "risk_status": self.audit_request_risk_status,
            "audit_package": dict(self.audit_request_package),
            "audit_package_hash": self.audit_request_package_hash,
            "continuation_frozen": self.audit_request_continuation_frozen,
            "continuation_status": self.audit_request_continuation_status,
            "traceability_preserved": (
                self.audit_request_traceability_preserved
            ),
            "delivery_targets": list(self.audit_request_delivery_targets),
            "delivery_status": self.audit_request_delivery_status,
            "audit_lifecycle": [
                dict(entry) for entry in self.audit_request_lifecycle
            ],
            "modified_files": list(self.audit_request_modified_files),
            "detected_risks": list(self.audit_request_detected_risks),
            "provider_context": dict(self.audit_request_provider_context),
            "runtime_state": dict(self.audit_request_runtime_state),
            "duration_ms": self.audit_request_duration_ms,
            "reasons": list(self.audit_request_reasons),
            "last_error": self.audit_request_last_error,
            "metadata": dict(self.audit_request_metadata),
        }

    def audit_response_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_audit_response_at": fmt(self.last_audit_response_at),
            "audit_response_iteration": self.audit_response_iteration,
            "audit_response_status": self.audit_response_status,
            "audit_responses_approved": self.audit_responses_approved,
            "audit_responses_warning": self.audit_responses_warning,
            "audit_responses_needs_fix": self.audit_responses_needs_fix,
            "audit_responses_rejected": self.audit_responses_rejected,
            "audit_response_errors": self.audit_response_errors,
            "response_id": self.last_audit_response_id,
            "audit_id": self.audit_response_audit_id,
            "execution_id": self.audit_response_execution_id,
            "task_id": self.audit_response_task_id,
            "audit_result": self.audit_response_result,
            "risk_level": self.audit_response_risk_level,
            "correction_status": self.audit_response_correction_status,
            "continuation_status": self.audit_response_continuation_status,
            "human_approval_status": (
                self.audit_response_human_approval_status
            ),
            "security_escalation_status": (
                self.audit_response_security_escalation_status
            ),
            "centinela_escalation": self.audit_response_centinela_escalation,
            "execution_decision": self.audit_response_execution_decision,
            "context_preserved": self.audit_response_context_preserved,
            "audit_integrity_preserved": (
                self.audit_response_integrity_preserved
            ),
            "warnings": list(self.audit_response_warnings),
            "detected_risks": list(self.audit_response_detected_risks),
            "rejection_reasons": list(self.audit_response_rejection_reasons),
            "correction_requirements": list(
                self.audit_response_correction_requirements
            ),
            "modified_files": list(self.audit_response_modified_files),
            "audit_logs": [dict(entry) for entry in self.audit_response_logs],
            "audit_lifecycle": [
                dict(entry) for entry in self.audit_response_lifecycle
            ],
            "execution_context": dict(self.audit_response_execution_context),
            "duration_ms": self.audit_response_duration_ms,
            "reasons": list(self.audit_response_reasons),
            "last_error": self.audit_response_last_error,
            "metadata": dict(self.audit_response_metadata),
        }

    def approval_gate_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_approval_gate_at": fmt(self.last_approval_gate_at),
            "approval_gate_iteration": self.approval_gate_iteration,
            "approval_gate_status": self.approval_gate_status,
            "approval_requests_pending": self.approval_requests_pending,
            "approval_decisions_approved": self.approval_decisions_approved,
            "approval_decisions_rejected": self.approval_decisions_rejected,
            "approval_decisions_needs_changes": (
                self.approval_decisions_needs_changes
            ),
            "approval_decisions_escalated": (
                self.approval_decisions_escalated
            ),
            "approval_gate_errors": self.approval_gate_errors,
            "approval_id": self.last_approval_id,
            "execution_id": self.approval_gate_execution_id,
            "task_id": self.approval_gate_task_id,
            "approval_type": self.approval_gate_type,
            "approval_status": self.approval_gate_approval_status,
            "audit_status": self.approval_gate_audit_status,
            "human_decision": self.approval_gate_human_decision,
            "continuation_status": self.approval_gate_continuation_status,
            "risk_status": self.approval_gate_risk_status,
            "governance_status": self.approval_gate_governance_status,
            "context_preserved": self.approval_gate_context_preserved,
            "human_authority_preserved": (
                self.approval_gate_human_authority_preserved
            ),
            "autonomy_blocked": self.approval_gate_autonomy_blocked,
            "decided_by": self.approval_gate_decided_by,
            "decision_reason": self.approval_gate_decision_reason,
            "human_report": dict(self.approval_gate_human_report),
            "modified_files": list(self.approval_gate_modified_files),
            "detected_risks": list(self.approval_gate_detected_risks),
            "warnings": list(self.approval_gate_warnings),
            "approval_lifecycle": [
                dict(entry) for entry in self.approval_gate_lifecycle
            ],
            "execution_context": dict(self.approval_gate_execution_context),
            "duration_ms": self.approval_gate_duration_ms,
            "reasons": list(self.approval_gate_reasons),
            "last_error": self.approval_gate_last_error,
            "metadata": dict(self.approval_gate_metadata),
        }

    def execution_blocking_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_execution_blocking_at": fmt(
                self.last_execution_blocking_at
            ),
            "execution_blocking_iteration": self.execution_blocking_iteration,
            "execution_blocking_status": self.execution_blocking_status,
            "execution_blocks_active": self.execution_blocks_active,
            "execution_blocks_invalid": self.execution_blocks_invalid,
            "execution_blocking_errors": self.execution_blocking_errors,
            "block_id": self.last_execution_block_id,
            "execution_id": self.execution_block_execution_id,
            "task_id": self.execution_block_task_id,
            "block_type": self.execution_block_type,
            "block_status": self.execution_block_status,
            "block_classification": self.execution_block_classification,
            "block_reason": self.execution_block_reason,
            "risk_level": self.execution_block_risk_level,
            "escalation_status": self.execution_block_escalation_status,
            "continuation_status": self.execution_block_continuation_status,
            "execution_frozen": self.execution_block_execution_frozen,
            "continuation_blocked": self.execution_block_continuation_blocked,
            "context_preserved": self.execution_block_context_preserved,
            "governance_protected": self.execution_block_governance_protected,
            "security_authority_required": (
                self.execution_block_security_authority_required
            ),
            "human_authority_required": (
                self.execution_block_human_authority_required
            ),
            "modified_files": list(self.execution_block_modified_files),
            "runtime_logs": [
                dict(entry) for entry in self.execution_block_runtime_logs
            ],
            "audit_history": [
                dict(entry) for entry in self.execution_block_audit_history
            ],
            "risk_history": list(self.execution_block_risk_history),
            "runtime_state": dict(self.execution_block_runtime_state),
            "provider_context": dict(self.execution_block_provider_context),
            "execution_context": dict(self.execution_block_execution_context),
            "blocking_lifecycle": [
                dict(entry) for entry in self.execution_block_lifecycle
            ],
            "duration_ms": self.execution_block_duration_ms,
            "reasons": list(self.execution_block_reasons),
            "last_error": self.execution_block_last_error,
            "metadata": dict(self.execution_block_metadata),
        }

    def phase_continuation_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_phase_continuation_at": fmt(
                self.last_phase_continuation_at
            ),
            "phase_continuation_iteration": (
                self.phase_continuation_iteration
            ),
            "phase_continuation_status": self.phase_continuation_status,
            "phase_continuations_ready": self.phase_continuations_ready,
            "phase_continuations_blocked": self.phase_continuations_blocked,
            "phase_continuations_completed": self.phase_continuations_completed,
            "phase_continuation_errors": self.phase_continuation_errors,
            "continuation_id": self.last_phase_continuation_id,
            "current_phase": self.phase_continuation_current_phase,
            "current_subphase": self.phase_continuation_current_subphase,
            "next_subphase": self.phase_continuation_next_subphase,
            "continuation_type": self.phase_continuation_type,
            "governance_status": self.phase_continuation_governance_status,
            "audit_status": self.phase_continuation_audit_status,
            "execution_status": self.phase_continuation_execution_status,
            "continuation_status": self.phase_continuation_runtime_status,
            "roadmap_loaded": self.phase_continuation_roadmap_loaded,
            "dependencies_satisfied": (
                self.phase_continuation_dependencies_satisfied
            ),
            "governance_satisfied": (
                self.phase_continuation_governance_satisfied
            ),
            "audit_satisfied": self.phase_continuation_audit_satisfied,
            "execution_stable": self.phase_continuation_execution_stable,
            "runtime_safe": self.phase_continuation_runtime_safe,
            "context_preserved": self.phase_continuation_context_preserved,
            "traceability_preserved": (
                self.phase_continuation_traceability_preserved
            ),
            "progression_allowed": (
                self.phase_continuation_progression_allowed
            ),
            "roadmap": list(self.phase_continuation_roadmap),
            "completed_subphases": list(
                self.phase_continuation_completed_subphases
            ),
            "required_dependencies": list(
                self.phase_continuation_required_dependencies
            ),
            "missing_dependencies": list(
                self.phase_continuation_missing_dependencies
            ),
            "execution_context": dict(
                self.phase_continuation_execution_context
            ),
            "lifecycle_history": [
                dict(entry)
                for entry in self.phase_continuation_lifecycle_history
            ],
            "audit_history": [
                dict(entry) for entry in self.phase_continuation_audit_history
            ],
            "governance_history": [
                dict(entry)
                for entry in self.phase_continuation_governance_history
            ],
            "continuation_lifecycle": [
                dict(entry) for entry in self.phase_continuation_lifecycle
            ],
            "duration_ms": self.phase_continuation_duration_ms,
            "reasons": list(self.phase_continuation_reasons),
            "last_error": self.phase_continuation_last_error,
            "metadata": dict(self.phase_continuation_metadata),
        }

    def checkpoint_recovery_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_checkpoint_recovery_at": fmt(
                self.last_checkpoint_recovery_at
            ),
            "checkpoint_recovery_iteration": self.checkpoint_recovery_iteration,
            "checkpoint_recovery_status": self.checkpoint_recovery_status,
            "checkpoints_created": self.checkpoints_created,
            "checkpoint_recoveries_prepared": (
                self.checkpoint_recoveries_prepared
            ),
            "checkpoint_recoveries_blocked": self.checkpoint_recoveries_blocked,
            "checkpoint_recovery_errors": self.checkpoint_recovery_errors,
            "checkpoint_id": self.last_checkpoint_id,
            "recovery_id": self.last_recovery_id,
            "execution_id": self.checkpoint_execution_id,
            "task_id": self.checkpoint_task_id,
            "checkpoint_type": self.checkpoint_type,
            "recovery_status": self.checkpoint_recovery_state,
            "checkpoint_valid": self.checkpoint_valid,
            "checkpoint_checksum": self.checkpoint_checksum,
            "restoration_ready": self.checkpoint_restoration_ready,
            "continuation_status": self.checkpoint_continuation_status,
            "context_preserved": self.checkpoint_context_preserved,
            "traceability_preserved": self.checkpoint_traceability_preserved,
            "governance_review_required": (
                self.checkpoint_governance_review_required
            ),
            "audit_review_required": self.checkpoint_audit_review_required,
            "checkpoint": dict(self.checkpoint_payload),
            "restored_state": dict(self.checkpoint_restored_state),
            "phase_state": dict(self.checkpoint_phase_state),
            "runtime_state": dict(self.checkpoint_runtime_state),
            "governance_state": dict(self.checkpoint_governance_state),
            "audit_state": dict(self.checkpoint_audit_state),
            "provider_state": dict(self.checkpoint_provider_state),
            "execution_context": dict(self.checkpoint_execution_context),
            "lifecycle_state": dict(self.checkpoint_lifecycle_state),
            "modified_files": list(self.checkpoint_modified_files),
            "recovery_logs": [
                dict(entry) for entry in self.checkpoint_recovery_logs
            ],
            "recovery_lifecycle": [
                dict(entry) for entry in self.checkpoint_recovery_lifecycle
            ],
            "duration_ms": self.checkpoint_recovery_duration_ms,
            "reasons": list(self.checkpoint_recovery_reasons),
            "last_error": self.checkpoint_recovery_last_error,
            "metadata": dict(self.checkpoint_recovery_metadata),
        }

    def execution_resume_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_execution_resume_at": fmt(self.last_execution_resume_at),
            "execution_resume_iteration": self.execution_resume_iteration,
            "execution_resume_status": self.execution_resume_status,
            "execution_resumes_completed": self.execution_resumes_completed,
            "execution_resumes_blocked": self.execution_resumes_blocked,
            "execution_resume_errors": self.execution_resume_errors,
            "resume_id": self.last_resume_id,
            "execution_id": self.resume_execution_id,
            "task_id": self.resume_task_id,
            "checkpoint_id": self.resume_checkpoint_id,
            "resume_type": self.resume_type,
            "governance_status": self.resume_governance_status,
            "audit_status": self.resume_audit_status,
            "resume_status": self.resume_state,
            "continuation_status": self.resume_continuation_status,
            "runtime_stable": self.resume_runtime_stable,
            "checkpoint_valid": self.resume_checkpoint_valid,
            "execution_consistent": self.resume_execution_consistent,
            "governance_satisfied": self.resume_governance_satisfied,
            "audit_satisfied": self.resume_audit_satisfied,
            "workflow_continuity_preserved": (
                self.resume_workflow_continuity_preserved
            ),
            "execution_reactivated": self.resume_execution_reactivated,
            "context_restored": self.resume_context_restored,
            "context_preserved": self.resume_context_preserved,
            "traceability_preserved": self.resume_traceability_preserved,
            "provider_context_restored": self.resume_provider_context_restored,
            "restored_state": dict(self.resume_restored_state),
            "execution_context": dict(self.resume_execution_context),
            "lifecycle_state": dict(self.resume_lifecycle_state),
            "runtime_state": dict(self.resume_runtime_state),
            "governance_state": dict(self.resume_governance_state),
            "audit_state": dict(self.resume_audit_state),
            "provider_state": dict(self.resume_provider_state),
            "lifecycle_history": [
                dict(entry) for entry in self.resume_lifecycle_history
            ],
            "audit_history": [
                dict(entry) for entry in self.resume_audit_history
            ],
            "governance_history": [
                dict(entry) for entry in self.resume_governance_history
            ],
            "recovery_history": [
                dict(entry) for entry in self.resume_recovery_history
            ],
            "modified_files": list(self.resume_modified_files),
            "resume_lifecycle": [
                dict(entry) for entry in self.resume_lifecycle
            ],
            "duration_ms": self.execution_resume_duration_ms,
            "reasons": list(self.execution_resume_reasons),
            "last_error": self.execution_resume_last_error,
            "metadata": dict(self.execution_resume_metadata),
        }

    def workflow_chaining_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_workflow_chaining_at": fmt(self.last_workflow_chaining_at),
            "workflow_chaining_iteration": self.workflow_chaining_iteration,
            "workflow_chaining_status": self.workflow_chaining_status,
            "workflow_chains_activated": self.workflow_chains_activated,
            "workflow_chains_blocked": self.workflow_chains_blocked,
            "workflow_chains_completed": self.workflow_chains_completed,
            "workflow_chaining_errors": self.workflow_chaining_errors,
            "chaining_id": self.last_chaining_id,
            "current_workflow": self.chaining_current_workflow,
            "next_workflow": self.chaining_next_workflow,
            "current_phase": self.chaining_current_phase,
            "current_subphase": self.chaining_current_subphase,
            "chaining_type": self.chaining_type,
            "governance_status": self.chaining_governance_status,
            "audit_status": self.chaining_audit_status,
            "execution_status": self.chaining_execution_status,
            "dependency_status": self.chaining_dependency_status,
            "continuation_status": self.chaining_continuation_status,
            "roadmap_loaded": self.chaining_roadmap_loaded,
            "current_workflow_completed": (
                self.chaining_current_workflow_completed
            ),
            "dependencies_satisfied": self.chaining_dependencies_satisfied,
            "governance_satisfied": self.chaining_governance_satisfied,
            "audit_satisfied": self.chaining_audit_satisfied,
            "execution_stable": self.chaining_execution_stable,
            "runtime_safe": self.chaining_runtime_safe,
            "progression_allowed": self.chaining_progression_allowed,
            "workflow_activation": self.chaining_workflow_activation,
            "context_preserved": self.chaining_context_preserved,
            "traceability_preserved": self.chaining_traceability_preserved,
            "roadmap": list(self.chaining_roadmap),
            "completed_workflows": list(self.chaining_completed_workflows),
            "required_dependencies": list(self.chaining_required_dependencies),
            "missing_dependencies": list(self.chaining_missing_dependencies),
            "next_workflow_context": dict(self.chaining_next_workflow_context),
            "execution_context": dict(self.chaining_execution_context),
            "lifecycle_history": [
                dict(entry) for entry in self.chaining_lifecycle_history
            ],
            "roadmap_history": [
                dict(entry) for entry in self.chaining_roadmap_history
            ],
            "governance_history": [
                dict(entry) for entry in self.chaining_governance_history
            ],
            "audit_history": [
                dict(entry) for entry in self.chaining_audit_history
            ],
            "chaining_lifecycle": [
                dict(entry) for entry in self.chaining_lifecycle
            ],
            "duration_ms": self.workflow_chaining_duration_ms,
            "reasons": list(self.workflow_chaining_reasons),
            "last_error": self.workflow_chaining_last_error,
            "metadata": dict(self.workflow_chaining_metadata),
        }

    def continuation_safety_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_continuation_safety_at": fmt(
                self.last_continuation_safety_at
            ),
            "continuation_safety_iteration": (
                self.continuation_safety_iteration
            ),
            "continuation_safety_status": self.continuation_safety_status,
            "continuations_safe": self.continuations_safe,
            "continuations_warning": self.continuations_warning,
            "continuations_blocked": self.continuations_blocked,
            "continuations_critical": self.continuations_critical,
            "continuation_safety_errors": self.continuation_safety_errors,
            "safety_id": self.last_safety_id,
            "execution_id": self.safety_execution_id,
            "task_id": self.safety_task_id,
            "safety_type": self.safety_type,
            "current_workflow": self.safety_current_workflow,
            "next_workflow": self.safety_next_workflow,
            "continuation_status": self.safety_continuation_status,
            "governance_status": self.safety_governance_status,
            "audit_status": self.safety_audit_status,
            "security_status": self.safety_security_status,
            "risk_level": self.safety_risk_level,
            "governance_valid": self.safety_governance_valid,
            "audit_valid": self.safety_audit_valid,
            "security_clear": self.safety_security_clear,
            "runtime_stable": self.safety_runtime_stable,
            "dependencies_complete": self.safety_dependencies_complete,
            "execution_consistent": self.safety_execution_consistent,
            "workflow_integrity": self.safety_workflow_integrity,
            "continuation_allowed": self.safety_continuation_allowed,
            "human_review_required": self.safety_human_review_required,
            "sentinel_escalation_required": (
                self.safety_sentinel_escalation_required
            ),
            "centinela_escalation_required": (
                self.safety_centinela_escalation_required
            ),
            "autonomy_limited": self.safety_autonomy_limited,
            "context_preserved": self.safety_context_preserved,
            "traceability_preserved": self.safety_traceability_preserved,
            "detected_risks": list(self.safety_detected_risks),
            "warnings": list(self.safety_warnings),
            "security_events": [
                dict(entry) for entry in self.safety_security_events
            ],
            "continuation_logs": [
                dict(entry) for entry in self.safety_continuation_logs
            ],
            "execution_context": dict(self.safety_execution_context),
            "governance_history": [
                dict(entry) for entry in self.safety_governance_history
            ],
            "audit_history": [
                dict(entry) for entry in self.safety_audit_history
            ],
            "workflow_history": [
                dict(entry) for entry in self.safety_workflow_history
            ],
            "safety_lifecycle": [
                dict(entry) for entry in self.safety_lifecycle
            ],
            "duration_ms": self.continuation_safety_duration_ms,
            "reasons": list(self.continuation_safety_reasons),
            "last_error": self.continuation_safety_last_error,
            "metadata": dict(self.continuation_safety_metadata),
        }

    def operational_memory_metrics(self) -> dict:
        def fmt(value: datetime | None):
            return value.isoformat() if value else None

        return {
            "last_operational_memory_at": fmt(
                self.last_operational_memory_at
            ),
            "operational_memory_iteration": self.operational_memory_iteration,
            "operational_memory_status": self.operational_memory_status,
            "memories_captured": self.memories_captured,
            "memories_retrieved": self.memories_retrieved,
            "memories_blocked": self.memories_blocked,
            "operational_memory_errors": self.operational_memory_errors,
            "memory_id": self.last_memory_id,
            "execution_id": self.memory_execution_id,
            "task_id": self.memory_task_id,
            "memory_type": self.memory_type,
            "workflow": self.memory_workflow,
            "event_type": self.memory_event_type,
            "governance_status": self.memory_governance_status,
            "audit_status": self.memory_audit_status,
            "risk_level": self.memory_risk_level,
            "memory_context": dict(self.memory_context),
            "memory_record": dict(self.memory_record),
            "memory_records": [
                dict(record) for record in self.memory_records
            ],
            "reusable_context": dict(self.memory_reusable_context),
            "integrity_valid": self.memory_integrity_valid,
            "context_safe": self.memory_context_safe,
            "governance_safe": self.memory_governance_safe,
            "traceability_preserved": self.memory_traceability_preserved,
            "reuse_allowed": self.memory_reuse_allowed,
            "critical_memory_preserved": self.memory_critical_preserved,
            "matched_records": self.memory_matched_records,
            "corrupt_records": self.memory_corrupt_records,
            "errors": list(self.memory_errors),
            "warnings": list(self.memory_warnings),
            "governance_history": [
                dict(entry) for entry in self.memory_governance_history
            ],
            "audit_history": [
                dict(entry) for entry in self.memory_audit_history
            ],
            "workflow_history": [
                dict(entry) for entry in self.memory_workflow_history
            ],
            "continuation_history": [
                dict(entry) for entry in self.memory_continuation_history
            ],
            "memory_lifecycle": [
                dict(entry) for entry in self.memory_lifecycle
            ],
            "duration_ms": self.operational_memory_duration_ms,
            "reasons": list(self.operational_memory_reasons),
            "last_error": self.operational_memory_last_error,
            "metadata": dict(self.operational_memory_metadata),
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
            "prompt_execution": self.prompt_execution_metrics(),
            "provider_response_handling": (
                self.provider_response_handling_metrics()
            ),
            "provider_failure_control": self.provider_failure_control_metrics(),
            "provider_routing": self.provider_routing_metrics(),
            "self_validation": self.self_validation_metrics(),
            "audit_request": self.audit_request_metrics(),
            "audit_response": self.audit_response_metrics(),
            "approval_gate": self.approval_gate_metrics(),
            "execution_blocking": self.execution_blocking_metrics(),
            "phase_continuation": self.phase_continuation_metrics(),
            "checkpoint_recovery": self.checkpoint_recovery_metrics(),
            "execution_resume": self.execution_resume_metrics(),
            "workflow_chaining": self.workflow_chaining_metrics(),
            "continuation_safety": self.continuation_safety_metrics(),
            "operational_memory": self.operational_memory_metrics(),
            "response_ingestion": self.response_ingestion_metrics(),
            "response_validation": self.response_validation_metrics(),
            "response_safety": self.response_safety_metrics(),
            "safety": self.safety_metrics(),
        }
        data.update(self.ai_metrics())
        data.update(self.telegram_metrics())
        return data


runtime_status = RuntimeStatus()
