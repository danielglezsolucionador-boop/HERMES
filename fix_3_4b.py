"""
fix_3_4b.py — Corrige el string literal roto en handle_tasks
"""

handler_path = r"C:\Users\admin\knowledge-core\hermes\app\telegram\handler.py"

with open(handler_path, "r", encoding="utf-8") as f:
    src = f.read()

# La línea rota tiene un newline literal dentro del string join
OLD_LINE = '    await send_message("\n".join(lines), chat_id=chat_id)'
NEW_LINE = '    await send_message("\\n".join(lines), chat_id=chat_id)'

# Buscar variantes — el archivo puede tener el newline literal
import re
# Reemplazar cualquier forma rota del join
src_fixed = re.sub(
    r'await send_message\(\s*["\'][\n\r]+["\']\.join\(lines\)',
    'await send_message("\\n".join(lines)',
    src
)

if src_fixed == src:
    # Intentar match exacto
    if OLD_LINE in src:
        src_fixed = src.replace(OLD_LINE, NEW_LINE)
        print("✅ Fix aplicado (match exacto)")
    else:
        print("❌ No se encontró el patrón — revisar manualmente")
else:
    print("✅ Fix aplicado (regex)")

with open(handler_path, "w", encoding="utf-8") as f:
    f.write(src_fixed)

print("Validando...")
import py_compile
try:
    py_compile.compile(handler_path, doraise=True)
    print("✅ handler.py — sintaxis OK")
except py_compile.PyCompileError as e:
    print(f"❌ Aún hay error: {e}")