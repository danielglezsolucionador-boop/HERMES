content = open('app/models/task.py', 'r', encoding='utf-8').read()

# 1. Cambiar estados
old_status = '''class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"'''

new_status = '''class TaskStatus(str, Enum):
    pending = "pending"
    doing = "doing"
    review = "review"
    done = "done"
    failed = "failed"'''

assert old_status in content, 'STATUS NO ENCONTRADO'
content = content.replace(old_status, new_status)

# 2. Renombrar name → title y agregar description y phase
old_fields = '''    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=TaskStatus.pending, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)'''

new_fields = '''    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=TaskStatus.pending, nullable=False)
    phase: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)'''

assert old_fields in content, 'FIELDS NO ENCONTRADO'
content = content.replace(old_fields, new_fields)

open('app/models/task.py', 'w', encoding='utf-8').write(content)
print('OK - task.py actualizado incrementalmente')