import unicodedata

path = r"app\ai\guardrails.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Reemplazar el metodo validate_response para normalizar antes de comparar
old_detect = '        # Detectar patrones peligrosos\n        response_lower = response.lower()\n        for pattern in DANGEROUS_PATTERNS:\n            if pattern in response_lower:'

new_detect = '''        # Detectar patrones peligrosos — normalizar tildes para comparacion robusta
        def _strip_accents(s):
            return "".join(
                c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn"
            )
        response_normalized = _strip_accents(response.lower())
        for pattern in DANGEROUS_PATTERNS:
            if _strip_accents(pattern) in response_normalized:'''

assert old_detect in content, "ERROR: bloque detect no encontrado"
content = content.replace(old_detect, new_detect, 1)

# Agregar import unicodedata al inicio
old_import = "import logging\nimport time"
new_import = "import logging\nimport time\nimport unicodedata"

assert old_import in content, "ERROR: imports no encontrados"
content = content.replace(old_import, new_import, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK — guardrails.py actualizado con normalizacion de tildes")