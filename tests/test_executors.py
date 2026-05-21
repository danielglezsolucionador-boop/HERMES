from app.runner.executors import is_ai_task_payload


def test_is_ai_task_payload_detects_explicit_ai_executor():
    assert is_ai_task_payload({"executor": "ai"}) is True
    assert is_ai_task_payload({"type": "llm"}) is True


def test_is_ai_task_payload_detects_provider_aliases():
    assert is_ai_task_payload({"agent": "deepseek"}) is True
    assert is_ai_task_payload({"provider": "openrouter"}) is True
    assert is_ai_task_payload({"model": "deepseek/deepseek-chat"}) is True
    assert is_ai_task_payload({"model": "gpt-4.1-mini"}) is True


def test_is_ai_task_payload_keeps_default_payloads_non_ai():
    assert is_ai_task_payload({"executor": "default"}) is False
    assert is_ai_task_payload({"sequence": 1, "expected": "done"}) is False
    assert is_ai_task_payload({}) is False
