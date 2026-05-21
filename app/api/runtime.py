import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_session
from app.models.task import Task
from app.services.operational_health import build_operational_health
from app.services.runtime_status import runtime_status as runner_runtime_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime", tags=["runtime"])


@router.get("/status")
async def runtime_status(session: AsyncSession = Depends(get_session)):
    try:
        # Conteos por status
        result = await session.execute(
            select(Task.status, func.count(Task.id)).group_by(Task.status)
        )
        counts = {row[0]: row[1] for row in result.all()}

        total = sum(counts.values())
        done = counts.get("done", 0)
        failed = counts.get("failed", 0)
        doing = counts.get("doing", 0)
        claimed = counts.get("claimed", 0)
        review = counts.get("review", 0)
        running_legacy = counts.get("running", 0)
        pending = counts.get("pending", 0)
        ai_metrics = runner_runtime_status.ai_metrics()
        telegram_metrics = runner_runtime_status.telegram_metrics()
        runtime_loop_metrics = runner_runtime_status.runtime_loop_metrics()
        polling_metrics = runner_runtime_status.polling_metrics()
        discovery_metrics = runner_runtime_status.discovery_metrics()
        claiming_metrics = runner_runtime_status.claiming_metrics()
        pickup_safety_metrics = runner_runtime_status.pickup_safety_metrics()
        execution_metrics = runner_runtime_status.execution_metrics()
        execution_session_metrics = (
            runner_runtime_status.execution_session_metrics()
        )
        execution_safety_metrics = runner_runtime_status.execution_safety_metrics()
        timeout_control_metrics = runner_runtime_status.timeout_control_metrics()
        retry_control_metrics = runner_runtime_status.retry_control_metrics()
        orchestration_metrics = runner_runtime_status.orchestration_metrics()
        orchestration_safety_metrics = (
            runner_runtime_status.orchestration_safety_metrics()
        )
        provider_bridge_metrics = runner_runtime_status.provider_bridge_metrics()
        prompt_execution_metrics = runner_runtime_status.prompt_execution_metrics()
        provider_response_handling_metrics = (
            runner_runtime_status.provider_response_handling_metrics()
        )
        provider_failure_control_metrics = (
            runner_runtime_status.provider_failure_control_metrics()
        )
        provider_routing_metrics = runner_runtime_status.provider_routing_metrics()
        self_validation_metrics = runner_runtime_status.self_validation_metrics()
        audit_request_metrics = runner_runtime_status.audit_request_metrics()
        audit_response_metrics = runner_runtime_status.audit_response_metrics()
        approval_gate_metrics = runner_runtime_status.approval_gate_metrics()
        execution_blocking_metrics = (
            runner_runtime_status.execution_blocking_metrics()
        )
        phase_continuation_metrics = (
            runner_runtime_status.phase_continuation_metrics()
        )
        checkpoint_recovery_metrics = (
            runner_runtime_status.checkpoint_recovery_metrics()
        )
        execution_resume_metrics = runner_runtime_status.execution_resume_metrics()
        workflow_chaining_metrics = runner_runtime_status.workflow_chaining_metrics()
        continuation_safety_metrics = (
            runner_runtime_status.continuation_safety_metrics()
        )
        operational_memory_metrics = (
            runner_runtime_status.operational_memory_metrics()
        )
        workflow_learning_metrics = (
            runner_runtime_status.workflow_learning_metrics()
        )
        preference_adaptation_metrics = (
            runner_runtime_status.preference_adaptation_metrics()
        )
        learning_safety_metrics = (
            runner_runtime_status.learning_safety_metrics()
        )
        ecosystem_registry_metrics = (
            runner_runtime_status.ecosystem_registry_metrics()
        )
        executive_communication_metrics = (
            runner_runtime_status.executive_communication_metrics()
        )
        governance_foundation_metrics = (
            runner_runtime_status.governance_foundation_metrics()
        )
        approval_system_metrics = runner_runtime_status.approval_system_metrics()
        governance_escalation_metrics = (
            runner_runtime_status.governance_escalation_metrics()
        )
        governance_safety_metrics = (
            runner_runtime_status.governance_safety_metrics()
        )
        operational_task_discovery_metrics = (
            runner_runtime_status.operational_task_discovery_metrics()
        )
        vulcan_prompt_protocol_metrics = (
            runner_runtime_status.vulcan_prompt_protocol_metrics()
        )
        vulcan_scope_enforcement_metrics = (
            runner_runtime_status.vulcan_scope_enforcement_metrics()
        )
        vulcan_execution_handoff_metrics = (
            runner_runtime_status.vulcan_execution_handoff_metrics()
        )
        vulcan_operational_validation_metrics = (
            runner_runtime_status.vulcan_operational_validation_metrics()
        )
        sentinel_audit_pipeline_metrics = (
            runner_runtime_status.sentinel_audit_pipeline_metrics()
        )
        sentinel_technical_validation_metrics = (
            runner_runtime_status.sentinel_technical_validation_metrics()
        )
        sentinel_security_escalation_metrics = (
            runner_runtime_status.sentinel_security_escalation_metrics()
        )
        sentinel_audit_reporting_metrics = (
            runner_runtime_status.sentinel_audit_reporting_metrics()
        )
        knowledge_core_reader_metrics = (
            runner_runtime_status.knowledge_core_reader_metrics()
        )
        phases_roadmap_reader_metrics = (
            runner_runtime_status.phases_roadmap_reader_metrics()
        )
        apps_standards_reader_metrics = (
            runner_runtime_status.apps_standards_reader_metrics()
        )
        dependency_context_builder_metrics = (
            runner_runtime_status.dependency_context_builder_metrics()
        )
        knowledge_core_validation_metrics = (
            runner_runtime_status.knowledge_core_validation_metrics()
        )
        workflow_execution_engine_metrics = (
            runner_runtime_status.workflow_execution_engine_metrics()
        )
        multi_step_execution_control_metrics = (
            runner_runtime_status.multi_step_execution_control_metrics()
        )
        response_ingestion_metrics = runner_runtime_status.response_ingestion_metrics()
        response_validation_metrics = runner_runtime_status.response_validation_metrics()
        response_safety_metrics = runner_runtime_status.response_safety_metrics()
        safety_metrics = runner_runtime_status.safety_metrics()
        operational_health = await build_operational_health(session, counts)

        return {
            "status": "online",
            "uptime": "active",
            "tasks": {
                "total": total,
                "done": done,
                "failed": failed,
                "doing": doing,
                "claimed": claimed,
                "review": review,
                "pending": pending,
                "running_legacy": running_legacy,
            },
            "runner": runner_runtime_status.to_dict(),
            "runtime_loop": runtime_loop_metrics,
            "polling": polling_metrics,
            "discovery": discovery_metrics,
            "claiming": claiming_metrics,
            "pickup_safety": pickup_safety_metrics,
            "execution": execution_metrics,
            "execution_session": execution_session_metrics,
            "execution_safety": execution_safety_metrics,
            "timeout_control": timeout_control_metrics,
            "retry_control": retry_control_metrics,
            "orchestration": orchestration_metrics,
            "orchestration_safety": orchestration_safety_metrics,
            "provider_bridge": provider_bridge_metrics,
            "prompt_execution": prompt_execution_metrics,
            "provider_response_handling": provider_response_handling_metrics,
            "provider_failure_control": provider_failure_control_metrics,
            "provider_routing": provider_routing_metrics,
            "self_validation": self_validation_metrics,
            "audit_request": audit_request_metrics,
            "audit_response": audit_response_metrics,
            "approval_gate": approval_gate_metrics,
            "execution_blocking": execution_blocking_metrics,
            "phase_continuation": phase_continuation_metrics,
            "checkpoint_recovery": checkpoint_recovery_metrics,
            "execution_resume": execution_resume_metrics,
            "workflow_chaining": workflow_chaining_metrics,
            "continuation_safety": continuation_safety_metrics,
            "operational_memory": operational_memory_metrics,
            "workflow_learning": workflow_learning_metrics,
            "preference_adaptation": preference_adaptation_metrics,
            "learning_safety": learning_safety_metrics,
            "ecosystem_registry": ecosystem_registry_metrics,
            "executive_communication": executive_communication_metrics,
            "governance_foundation": governance_foundation_metrics,
            "approval_system": approval_system_metrics,
            "governance_escalation": governance_escalation_metrics,
            "governance_safety": governance_safety_metrics,
            "operational_task_discovery": operational_task_discovery_metrics,
            "vulcan_prompt_protocol": vulcan_prompt_protocol_metrics,
            "vulcan_scope_enforcement": vulcan_scope_enforcement_metrics,
            "vulcan_execution_handoff": vulcan_execution_handoff_metrics,
            "vulcan_operational_validation": (
                vulcan_operational_validation_metrics
            ),
            "sentinel_audit_pipeline": sentinel_audit_pipeline_metrics,
            "sentinel_technical_validation": (
                sentinel_technical_validation_metrics
            ),
            "sentinel_security_escalation": (
                sentinel_security_escalation_metrics
            ),
            "sentinel_audit_reporting": sentinel_audit_reporting_metrics,
            "knowledge_core_reader": knowledge_core_reader_metrics,
            "phases_roadmap_reader": phases_roadmap_reader_metrics,
            "apps_standards_reader": apps_standards_reader_metrics,
            "dependency_context_builder": (
                dependency_context_builder_metrics
            ),
            "knowledge_core_validation": (
                knowledge_core_validation_metrics
            ),
            "workflow_execution_engine": (
                workflow_execution_engine_metrics
            ),
            "multi_step_execution_control": (
                multi_step_execution_control_metrics
            ),
            "response_ingestion": response_ingestion_metrics,
            "response_validation": response_validation_metrics,
            "response_safety": response_safety_metrics,
            "safety": safety_metrics,
            "ai": ai_metrics,
            "telegram": telegram_metrics,
            "operational_health": operational_health,
            "operational_risks": operational_health.get("risks", []),
            "telegram_messages_processed": telegram_metrics["telegram_messages_processed"],
            "pipeline_avg_ms": ai_metrics["avg_ai_duration_ms"],
            "provider_avg_ms": ai_metrics["avg_ai_provider_duration_ms"],
            "db_context_avg_ms": ai_metrics["avg_ai_context_build_ms"],
        }
    except Exception as exc:
        logger.error("runtime/status error: %s", exc)
        return {"status": "degraded", "error": str(exc)}
