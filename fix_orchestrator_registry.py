path = r"app\ai\orchestrator.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1 — Reemplazar import claude_client por provider_registry
old_import = "from app.integrations.claude_client import ask"
new_import = "from app.ai.provider_registry import provider_registry, setup_registry"

assert old_import in content, "ERROR: import claude_client no encontrado"
content = content.replace(old_import, new_import, 1)

# 2 — Actualizar docstring clase
old_doc = "    Pipeline: build_context -> prompt -> claude_client.ask -> normalize."
new_doc = "    Pipeline: build_context -> prompt -> provider_registry -> provider.generate -> normalize."

assert old_doc in content, "ERROR: docstring clase no encontrado"
content = content.replace(old_doc, new_doc, 1)

# 3 — Reemplazar llamada directa a ask() por provider_registry
old_ask = "        system_prompt = guardrails.get_system_prompt()\n        claude_result = await ask(full_prompt, system_prompt=system_prompt)"
new_ask = """        # Step 3 — obtener provider activo via registry
        try:
            provider = provider_registry.get_active()
        except RuntimeError as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("orchestrator: provider no disponible=%s duration_ms=%d", exc, duration_ms)
            return self._error_response("provider_error", str(exc), duration_ms)

        health = await provider.healthcheck()
        if not health.get("configured"):
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(
                "orchestrator: provider='%s' configured=False duration_ms=%d",
                provider.provider_name, duration_ms,
            )
            return self._error_response("auth_failed", f"Provider '{provider.provider_name}' no configurado", duration_ms)

        system_prompt = guardrails.get_system_prompt()
        claude_result = await provider.generate(full_prompt, system_prompt=system_prompt)"""

assert old_ask in content, "ERROR: bloque ask no encontrado"
content = content.replace(old_ask, new_ask, 1)

# 4 — Actualizar log y retorno para usar provider_name dinamico
old_log = '            "orchestrator: claude fallo error_type=%s duration_ms=%d",'
new_log = '            "orchestrator: provider fallo error_type=%s duration_ms=%d",'

assert old_log in content, "ERROR: log fallo no encontrado"
content = content.replace(old_log, new_log, 1)

old_provider = '            "provider": "claude",'
new_provider = '            "provider": provider.provider_name,'

# Solo reemplazar el primero (en retorno exitoso)
assert old_provider in content, "ERROR: provider hardcoded no encontrado"
content = content.replace(old_provider, new_provider, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — orchestrator.py actualizado con provider_registry")