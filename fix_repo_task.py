content = open('app/repositories/task_repository.py', 'r', encoding='utf-8').read()

old = '''            task = Task(
                id=uuid.uuid4(),
                name=data.name or "task",
                payload=data.payload,
                status="pending",
                result=None,
                error=None,
            )'''

new = '''            task = Task(
                id=uuid.uuid4(),
                title=data.title or "task",
                description=data.description,
                phase=data.phase,
                payload=data.payload,
                status="pending",
                result=None,
                error=None,
            )'''

assert old in content, 'BLOQUE NO ENCONTRADO'
content = content.replace(old, new)
open('app/repositories/task_repository.py', 'w', encoding='utf-8').write(content)
print('OK - task_repository.py actualizado')