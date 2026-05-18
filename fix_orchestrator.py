path = r"app\ai\orchestrator.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1 — Actualizar docstring y agregar import guardrails
old_header = 'from app.integrations.claude_client import ask'
new_header = 'from app.integrations.claude_client import ask\nfrom app.ai.guardrails import guardrails'

assert old_header in content, "ERROR: import ask no encontrado"
content = content.replace(old_header, new_header, 1)

# 2 — Pasar system_prompt al ask()
old_ask = 'claude_result = await ask(full_prompt)'
new_ask = 'system_prompt = guardrails.get_system_prompt()\n        claude_result = await ask(full_prompt, system_prompt=system_prompt)'

assert old_ask in content, "ERROR: ask no encontrado"
content = content.replace(old_ask, new_ask, 1)

# 3 — Aplicar guardrails antes de retornar
old_return = '"response": claude_result.get("content", ""),'
new_return = '"response": guardrails.validate_response(claude_result.get("content", ""))["response"],'

assert old_return in content, "ERROR: response line no encontrada"
content = content.replace(old_return, new_return, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — orchestrator.py actualizado")