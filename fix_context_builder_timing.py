path = r"app\ai\context_builder.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1 — Agregar db_start timer y queries counter antes del bloque DB
old_db_start = "    try:\n        async with AsyncSessionLocal() as session:"
new_db_start = "    db_start = time.monotonic()\n    db_queries = 0\n    try:\n        async with AsyncSessionLocal() as session:"

assert old_db_start in content, "ERROR: bloque DB no encontrado"
content = content.replace(old_db_start, new_db_start, 1)

# 2 — Contar queries — failed
old_failed = '            failed, _ = await repo.list_tasks(limit=5, offset=0, status="failed")'
new_failed = '            failed, _ = await repo.list_tasks(limit=5, offset=0, status="failed")\n            db_queries += 2'

assert old_failed in content, "ERROR: query failed no encontrada"
content = content.replace(old_failed, new_failed, 1)

# 3 — Contar queries — doing
old_doing = '            doing, _ = await repo.list_tasks(limit=3, offset=0, status="doing")'
new_doing = '            doing, _ = await repo.list_tasks(limit=3, offset=0, status="doing")\n            db_queries += 2'

assert old_doing in content, "ERROR: query doing no encontrada"
content = content.replace(old_doing, new_doing, 1)

# 4 — Contar queries — pending
old_pending = '            pending, _ = await repo.list_tasks(limit=3, offset=0, status="pending")'
new_pending = '            pending, _ = await repo.list_tasks(limit=3, offset=0, status="pending")\n            db_queries += 2'

assert old_pending in content, "ERROR: query pending no encontrada"
content = content.replace(old_pending, new_pending, 1)

# 5 — Contar queries — done
old_done = '            done, _ = await repo.list_tasks(limit=3, offset=0, status="done")'
new_done = '            done, _ = await repo.list_tasks(limit=3, offset=0, status="done")\n            db_queries += 2'

assert old_done in content, "ERROR: query done no encontrada"
content = content.replace(old_done, new_done, 1)

# 6 — Calcular db_ms despues del bloque try/except
old_after_db = "    # Limitar totales"
new_after_db = "    db_ms = int((time.monotonic() - db_start) * 1000)\n\n    # Limitar totales"

assert old_after_db in content, "ERROR: bloque limitar totales no encontrado"
content = content.replace(old_after_db, new_after_db, 1)

# 7 — Agregar db_ms y db_queries al log final y retorno
old_log = '    logger.info(\n        "context_builder: completado tasks=%d incidents=%d chars=%d duration_ms=%d",\n        len(tasks_summary),\n        len(incidents),\n        context.get("_isolation", {}).get("total_chars", 0),\n        duration_ms,\n    )\n\n    return context'

new_log = '    logger.info(\n        "context_builder: completado tasks=%d incidents=%d chars=%d db_queries=%d db_ms=%d duration_ms=%d",\n        len(tasks_summary),\n        len(incidents),\n        context.get("_isolation", {}).get("total_chars", 0),\n        db_queries,\n        db_ms,\n        duration_ms,\n    )\n\n    context["_timing"] = {"db_ms": db_ms, "db_queries": db_queries, "total_ms": duration_ms}\n    return context'

assert old_log in content, "ERROR: log final no encontrado"
content = content.replace(old_log, new_log, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — context_builder.py actualizado con timing DB")