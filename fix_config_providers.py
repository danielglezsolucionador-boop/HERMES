path = r"app\core\config.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_claude = "    # Claude AI\n    CLAUDE_API_KEY: str = \"\""
new_claude = "    # Claude AI\n    CLAUDE_API_KEY: str = \"\"\n    # OpenRouter\n    OPENROUTER_API_KEY: str = \"\"\n    # AI Provider activo\n    AI_PROVIDER: str = \"openrouter\""

assert old_claude in content, "ERROR: bloque CLAUDE_API_KEY no encontrado"
content = content.replace(old_claude, new_claude, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — config.py actualizado con OPENROUTER_API_KEY y AI_PROVIDER")