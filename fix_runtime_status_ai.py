path = r"app\services\runtime_status.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1 — Agregar contadores IA en __init__
old_init_end = "        self.runner_alive: bool = False"
new_init_end = """        self.runner_alive: bool = False
        # AI observability
        self.ai_requests_total: int = 0
        self.ai_failures_total: int = 0
        self.ai_pipeline_ms_total: int = 0
        self.ai_provider_ms_total: int = 0
        self.ai_db_context_ms_total: int = 0"""

assert old_init_end in content, "ERROR: runner_alive no encontrado"
content = content.replace(old_init_end, new_init_end, 1)

# 2 — Agregar metodo mark_ai_request
old_mark_failed = "    def mark_task_failed(self):"
new_mark_ai = """    def mark_ai_request(self, success: bool, pipeline_ms: int, provider_ms: int, db_context_ms: int) -> None:
        \"\"\"Registra metricas de un request IA completado.\"\"\"
        self.ai_requests_total += 1
        if not success:
            self.ai_failures_total += 1
        self.ai_pipeline_ms_total += pipeline_ms
        self.ai_provider_ms_total += provider_ms
        self.ai_db_context_ms_total += db_context_ms

    def mark_task_failed(self):"""

assert old_mark_failed in content, "ERROR: mark_task_failed no encontrado"
content = content.replace(old_mark_failed, new_mark_ai, 1)

# 3 — Agregar metricas IA en to_dict
old_to_dict_end = '            "runtime_status": self.health_status(),\n        }'
new_to_dict_end = '''            "runtime_status": self.health_status(),
            "ai_requests_total": self.ai_requests_total,
            "ai_failures_total": self.ai_failures_total,
            "avg_pipeline_ms": round(self.ai_pipeline_ms_total / self.ai_requests_total) if self.ai_requests_total else 0,
            "avg_provider_ms": round(self.ai_provider_ms_total / self.ai_requests_total) if self.ai_requests_total else 0,
            "avg_db_context_ms": round(self.ai_db_context_ms_total / self.ai_requests_total) if self.ai_requests_total else 0,
        }'''

assert old_to_dict_end in content, "ERROR: to_dict end no encontrado"
content = content.replace(old_to_dict_end, new_to_dict_end, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — runtime_status.py actualizado con metricas IA")