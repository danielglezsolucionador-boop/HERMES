path = r"app\telegram\polling.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1 — Agregar handle_ask al import
old_import = "from app.telegram.handler import handle_message, handle_start, handle_status, handle_tasks, handle_task"
new_import = "from app.telegram.handler import handle_message, handle_start, handle_status, handle_tasks, handle_task, handle_ask"

assert old_import in content, "ERROR: import handler no encontrado"
content = content.replace(old_import, new_import, 1)

# 2 — Registrar CommandHandler ask
old_handler = '        _ptb_app.add_handler(CommandHandler("task", handle_task))'
new_handler = '        _ptb_app.add_handler(CommandHandler("task", handle_task))\n        _ptb_app.add_handler(CommandHandler("ask", handle_ask))'

assert old_handler in content, "ERROR: CommandHandler task no encontrado"
content = content.replace(old_handler, new_handler, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — handle_ask registrado en polling.py")