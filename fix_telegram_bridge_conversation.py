path = r"app\ai\telegram_bridge.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_import = "from app.ai.orchestrator import orchestrator"
new_import = """from app.ai.orchestrator import orchestrator
from app.db.engine import AsyncSessionLocal
from app.repositories.conversation_repository import save_message"""

assert old_import in content, "Import no encontrado"
content = content.replace(old_import, new_import, 1)

old_return = "        return self._format(response)\n\n    def _format"
new_return = """        try:
            async with AsyncSessionLocal() as session:
                await save_message(session, role="user", message=query)
                await save_message(session, role="hermes", message=response)
        except Exception as exc:
            logger.warning("telegram_bridge: error persistiendo conversacion: %s", exc)
        return self._format(response)

    def _format"""

assert old_return in content, "Fragmento return no encontrado"
content = content.replace(old_return, new_return, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK")