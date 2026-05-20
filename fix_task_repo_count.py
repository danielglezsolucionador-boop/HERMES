path = r"app\repositories\task_repository.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """            base_q = select(Task)
            if status:
                base_q = base_q.where(Task.status == status)

            count_result = await self.session.execute(
                select(func.count()).select_from(base_q.subquery())
            )
            total = count_result.scalar_one()"""

new = """            base_q = select(Task)
            if status:
                base_q = base_q.where(Task.status == status)

            count_q = select(func.count(Task.id))
            if status:
                count_q = count_q.where(Task.status == status)
            count_result = await self.session.execute(count_q)
            total = count_result.scalar_one()"""

assert old in content, "Fragmento no encontrado"
content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK")