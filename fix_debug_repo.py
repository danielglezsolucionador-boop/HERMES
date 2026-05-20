path = r"app\repositories\task_repository.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

idx = content.find("async def list_tasks")
print(repr(content[idx:idx+200]))