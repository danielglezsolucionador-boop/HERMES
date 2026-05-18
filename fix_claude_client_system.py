path = r"app\integrations\claude_client.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1 — Agregar system_prompt al signature de ask()
old_sig = "async def ask(prompt: str, max_tokens: int = 1024) -> dict:"
new_sig = "async def ask(prompt: str, max_tokens: int = 1024, system_prompt: str | None = None) -> dict:"

assert old_sig in content, "ERROR: signature ask no encontrada"
content = content.replace(old_sig, new_sig, 1)

# 2 — Agregar system al body si viene system_prompt
old_body = '''    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }'''

new_body = '''    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        body["system"] = system_prompt'''

assert old_body in content, "ERROR: body no encontrado"
content = content.replace(old_body, new_body, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — claude_client.py actualizado con system_prompt")