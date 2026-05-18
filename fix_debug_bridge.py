path = r"app\ai\telegram_bridge.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

idx = content.find("return self._format")
print(repr(content[idx-50:idx+80]))