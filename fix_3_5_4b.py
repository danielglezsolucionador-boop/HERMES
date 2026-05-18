"""
fix_3_5_4b.py — Agregar started_at y completed_at a TaskRead
"""

path = r"C:\Users\admin\knowledge-core\hermes\app\schemas\task.py"

with open(path, "r", encoding="utf-8") as f:
    src = f.read()

OLD = "    error: str | None\n    created_at: datetime"
NEW = "    error: str | None\n    started_at: datetime | None\n    completed_at: datetime | None\n    created_at: datetime"

assert OLD in src, "ERROR: campo error no encontrado en TaskRead"
src = src.replace(OLD, NEW, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("OK schemas/task.py — started_at, completed_at agregados a TaskRead")
except py_compile.PyCompileError as e:
    print("ERROR: {}".format(e))