from app.services.operational_risks import build_operational_risks


def test_operational_risks_derive_from_real_metrics_shape():
    health = {
        "checks": {
            "database": {"status": "healthy", "latency_ms": 10},
            "ai": {"status": "degraded", "last_error": "provider timeout"},
            "telegram": {"status": "healthy", "latency_ms": 20},
        }
    }
    task_counts = {"failed": 12, "doing": 3, "pending": 4}
    runtime = {
        "runner_status": "offline",
        "ai_requests_failed": 1,
        "telegram_messages_failed": 0,
        "ai_avg_duration_ms": 1000,
    }

    risks = build_operational_risks(health, task_counts, runtime)

    assert any(risk["source"] == "ai" for risk in risks)
    assert any(risk["message"] == "high failed tasks" for risk in risks)
    assert any(risk["source"] == "runtime" for risk in risks)
