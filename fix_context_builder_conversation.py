path = r"app\ai\context_builder.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_import = "from app.ai.context_isolation import build_operational_context, sanitize_text"

new_import = """from app.ai.context_isolation import build_operational_context, sanitize_text
from app.repositories.conversation_repository import get_recent as get_recent_conversation"""

assert old_import in content, "Import no encontrado"
content = content.replace(old_import, new_import, 1)

old_section = """    context["_timing"] = {"db_ms": db_ms, "db_queries": db_queries, "total_ms": duration_ms}
    return context"""

new_section = """    # Cargar conversacion reciente
    conversation_history = []
    try:
        async with AsyncSessionLocal() as session:
            conversation_history = await get_recent_conversation(session, limit=10)
    except Exception as exc:
        logger.warning("context_builder: error cargando conversacion: %s", exc)

    context["conversation_history"] = conversation_history
    context["_timing"] = {"db_ms": db_ms, "db_queries": db_queries, "total_ms": duration_ms}
    return context"""

assert old_section in content, "Seccion final no encontrada"
content = content.replace(old_section, new_section, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK")