path = r"app\repositories\task_repository.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """    async def list_tasks(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Task], int]:"""

new = """    async def list_tasks(
        self,
        limit: int = 20,
        offset: int = 0,
        status: str | None = None,
    ) -> tuple[list[Task], int]:"""

assert old in content, "Fragmento no encontrado"
content = content.replace(old, new, 1)

old2 = """            count_result = await self.session.execute(
                select(func.count()).select_from(Task)
            )
            total = count_result.scalar_one()

            rows_result = await self.session.execute(
                select(Task)
                .order_by(Task.created_at.desc())
                .limit(limit)
                .offset(offset)
            )"""

new2 = """            base_q = select(Task)
            if status:
                base_q = base_q.where(Task.status == status)

            count_result = await self.session.execute(
                select(func.count()).select_from(base_q.subquery())
            )
            total = count_result.scalar_one()

            rows_result = await self.session.execute(
                base_q
                .order_by(Task.created_at.desc())
                .limit(limit)
                .offset(offset)
            )"""

assert old2 in content, "Fragmento 2 no encontrado"
content = content.replace(old2, new2, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK")