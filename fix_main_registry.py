path = r"app\main.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1 — Agregar import setup_registry
old_import = "from app.integrations.claude_client import validate_startup"
new_import = "from app.integrations.claude_client import validate_startup\nfrom app.ai.provider_registry import setup_registry"

assert old_import in content, "ERROR: import validate_startup no encontrado"
content = content.replace(old_import, new_import, 1)

# 2 — Llamar setup_registry despues de validate_startup
old_validate = "    validate_startup()"
new_validate = "    validate_startup()\n    setup_registry()"

assert old_validate in content, "ERROR: validate_startup no encontrado"
content = content.replace(old_validate, new_validate, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — main.py actualizado con setup_registry")