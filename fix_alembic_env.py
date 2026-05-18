content = open('alembic/env.py', 'r', encoding='utf-8').read()

old = 'from app.db.base import Base'
new = 'from app.db.base import Base\nimport app.models  # noqa: F401 — registra todos los modelos'

assert old in content, 'NO ENCONTRADO'
content = content.replace(old, new)
open('alembic/env.py', 'w', encoding='utf-8').write(content)
print('OK - alembic/env.py actualizado con import modelos')