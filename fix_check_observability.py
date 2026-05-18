from app.services.runtime_status import runtime_status

s = runtime_status
print("ai_requests_total:", s.ai_requests_total)
print("ai_failures_total:", s.ai_failures_total)
print("avg_pipeline_ms:", s.avg_pipeline_ms)
print("avg_provider_ms:", s.avg_provider_ms)
print("avg_db_context_ms:", s.avg_db_context_ms)