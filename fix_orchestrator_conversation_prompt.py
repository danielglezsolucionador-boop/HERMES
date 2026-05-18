path = r"app\ai\orchestrator.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''def _build_prompt(context: dict) -> str:
    """Construye prompt seguro desde contexto ya sanitizado."""
    summary = context.get("summary", "")
    tasks = context.get("tasks", [])
    incidents = context.get("incidents", [])
    meta = context.get("metadata", {})
    parts = []
    parts.append("=== HERMES OPERATIONAL CONTEXT ===")
    parts.append(f"Status: {summary}")
    if meta:
        parts.append(f"Generated: {meta.get('generated_at', '')}")
    if tasks:
        parts.append("\\n=== TASKS ===")
        for t in tasks:
            line = f"[{t.get('status','').upper()}] {t.get('title','')}"
            if t.get("error"):
                line += f" | Error: {t['error']}"
            parts.append(line)
    if incidents:
        parts.append("\\n=== INCIDENTS ===")
        for i in incidents:
            parts.append(f"- {i}")
    return "\\n".join(parts)'''

new = '''def _build_prompt(context: dict) -> str:
    """Construye prompt seguro desde contexto ya sanitizado."""
    summary = context.get("summary", "")
    tasks = context.get("tasks", [])
    incidents = context.get("incidents", [])
    meta = context.get("metadata", {})
    conversation_history = context.get("conversation_history", [])
    parts = []
    parts.append("=== HERMES OPERATIONAL CONTEXT ===")
    parts.append(f"Status: {summary}")
    if meta:
        parts.append(f"Generated: {meta.get('generated_at', '')}")
    if tasks:
        parts.append("\\n=== TASKS ===")
        for t in tasks:
            line = f"[{t.get('status','').upper()}] {t.get('title','')}"
            if t.get("error"):
                line += f" | Error: {t['error']}"
            parts.append(line)
    if incidents:
        parts.append("\\n=== INCIDENTS ===")
        for i in incidents:
            parts.append(f"- {i}")
    if conversation_history:
        parts.append("\\n=== RECENT CONVERSATION ===")
        for msg in conversation_history:
            role = msg.get("role", "unknown").upper()
            message = msg.get("message", "")
            parts.append(f"[{role}] {message}")
    return "\\n".join(parts)'''

assert old in content, "Fragmento no encontrado"
content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK")