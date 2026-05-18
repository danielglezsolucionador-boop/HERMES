content = open('app/models/__init__.py', 'r', encoding='utf-8').read()

old = 'from app.models.task import Task\n\n__all__ = ["Task"]'
new = 'from app.models.task import Task\nfrom app.models.message import Message\n\n__all__ = ["Task", "Message"]'

assert old in content, 'NO ENCONTRADO'
content = content.replace(old, new)
open('app/models/__init__.py', 'w', encoding='utf-8').write(content)
print('OK - Message registrado en models/__init__.py')