path = r"app\main.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = "from fastapi import FastAPI"
new = "from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware"

assert old in content, "Import FastAPI no encontrado"
content = content.replace(old, new, 1)

old2 = "    app.include_router(api_router)\n    return app"
new2 = """    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "https://hermes-dashboard.vercel.app"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app"""

assert old2 in content, "include_router no encontrado"
content = content.replace(old2, new2, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK")