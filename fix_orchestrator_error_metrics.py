import re

path = r"app\ai\orchestrator.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''    def _error_response(self, error_type: str, error: str, duration_ms: int) -> dict:
        return {
            "success": False,
            "response": None,
            "provider": "claude",
            "duration_ms": duration_ms,
            "context_chars": 0,
            "tokens_estimated": 0,
            "fallback_used": False,
            "error": error_type,
        }'''

new = '''    def _error_response(self, error_type: str, error: str, duration_ms: int) -> dict:
        runtime_status.mark_ai_request(
            success=False,
            pipeline_ms=duration_ms,
            provider_ms=0,
            db_context_ms=0,
        )
        return {
            "success": False,
            "response": None,
            "provider": "claude",
            "duration_ms": duration_ms,
            "context_chars": 0,
            "tokens_estimated": 0,
            "fallback_used": False,
            "error": error_type,
        }'''

assert old in content, "Fragmento no encontrado"
content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK")