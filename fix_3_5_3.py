"""
fix_3_5_3.py — Fix: remover logger.warning duplicado en _persist_error
"""

path = r"C:\Users\admin\knowledge-core\hermes\app\runner\task_runner.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Buscar y eliminar la linea duplicada fuera del try en _persist_error
for i, l in enumerate(lines):
    if "no se pudo persistir error" in l:
        # La linea siguiente al except debe ser el logger.warning duplicado
        if i+1 < len(lines) and 'logger.warning("runner: task_id=%s -> failed' in lines[i+1]:
            del lines[i+1]
            print("OK — logger.warning duplicado eliminado (linea {})".format(i+2))
        break

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("OK sintaxis correcta")
except py_compile.PyCompileError as e:
    print("ERROR: {}".format(e))