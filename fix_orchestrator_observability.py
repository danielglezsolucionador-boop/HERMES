path = r"app\ai\orchestrator.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1 — Agregar import runtime_status
old_import = "from app.ai.guardrails import guardrails"
new_import = "from app.ai.guardrails import guardrails\nfrom app.services.runtime_status import runtime_status"

assert old_import in content, "ERROR: import guardrails no encontrado"
content = content.replace(old_import, new_import, 1)

# 2 — Agregar timing context_build — buscar por fragmento unico
old_ctx = "        context = await build_context()\n        isolation = context.get"
new_ctx = "        t_context_start = time.monotonic()\n        context = await build_context()\n        context_build_ms = int((time.monotonic() - t_context_start) * 1000)\n        isolation = context.get"

assert old_ctx in content, "ERROR: build_context no encontrado"
content = content.replace(old_ctx, new_ctx, 1)

# 3 — Agregar timing formatting
old_fmt = "        operational_prompt = _build_prompt(context)\n        full_prompt = operational_prompt"
new_fmt = "        t_format_start = time.monotonic()\n        operational_prompt = _build_prompt(context)\n        full_prompt = operational_prompt"

assert old_fmt in content, "ERROR: _build_prompt no encontrado"
content = content.replace(old_fmt, new_fmt, 1)

# 4 — Calcular formatting_ms antes de Step 3
old_step3 = "        # Step 3 \u2014 obtener provider activo via registry"
new_step3 = "        formatting_ms = int((time.monotonic() - t_format_start) * 1000)\n\n        # Step 3 \u2014 obtener provider activo via registry"

assert old_step3 in content, "ERROR: Step 3 no encontrado"
content = content.replace(old_step3, new_step3, 1)

# 5 — Agregar timing provider
old_gen = "        claude_result = await provider.generate(full_prompt, system_prompt=system_prompt)\n\n        duration_ms"
new_gen = "        t_provider_start = time.monotonic()\n        claude_result = await provider.generate(full_prompt, system_prompt=system_prompt)\n        provider_ms = int((time.monotonic() - t_provider_start) * 1000)\n\n        duration_ms"

assert old_gen in content, "ERROR: provider.generate no encontrado"
content = content.replace(old_gen, new_gen, 1)

# 6 — Reemplazar log final con timings detallados + mark_ai_request
old_log = '        logger.info(\n            "orchestrator: completado duration_ms=%d input_tokens=%d output_tokens=%d",\n            duration_ms,\n            usage.get("input_tokens", 0),\n            usage.get("output_tokens", 0),\n        )'
new_log = '        db_context_ms = context.get("_timing", {}).get("db_ms", 0)\n        db_queries = context.get("_timing", {}).get("db_queries", 0)\n        logger.info(\n            "orchestrator: completado provider=%s model=%s total_ms=%d "\n            "context_build_ms=%d db_ms=%d db_queries=%d format_ms=%d provider_ms=%d "\n            "input_tokens=%d output_tokens=%d chars_in=%d chars_out=%d",\n            provider.provider_name, claude_result.get("model", "unknown"),\n            duration_ms, context_build_ms, db_context_ms, db_queries,\n            formatting_ms, provider_ms,\n            usage.get("input_tokens", 0), usage.get("output_tokens", 0),\n            len(full_prompt), len(claude_result.get("content", "")),\n        )\n        runtime_status.mark_ai_request(\n            success=True,\n            pipeline_ms=duration_ms,\n            provider_ms=provider_ms,\n            db_context_ms=db_context_ms,\n        )'

assert old_log in content, "ERROR: log final no encontrado"
content = content.replace(old_log, new_log, 1)

# 7 — Reemplazar retorno exitoso con timings
old_return = '            "tokens_estimated": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),\n            "fallback_used": False,\n            "error": None,\n        }'
new_return = '            "tokens_estimated": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),\n            "model": claude_result.get("model", "unknown"),\n            "timings": {\n                "context_build_ms": context_build_ms,\n                "db_context_ms": db_context_ms,\n                "db_queries": db_queries,\n                "formatting_ms": formatting_ms,\n                "provider_ms": provider_ms,\n                "total_ms": duration_ms,\n            },\n            "fallback_used": False,\n            "error": None,\n        }'

assert old_return in content, "ERROR: retorno no encontrado"
content = content.replace(old_return, new_return, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — orchestrator.py actualizado con observabilidad")