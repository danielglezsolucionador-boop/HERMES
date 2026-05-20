path = r"app\telegram\polling.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '    logger.info("Telegram polling \u2192 activo \u2705")'

new = '''    logger.info("Telegram polling \u2192 activo \u2705")

_app = None

async def stop_polling() -> None:
    """Detiene el polling de Telegram."""
    global _app
    if _app:
        try:
            await _app.updater.stop()
            await _app.stop()
            await _app.shutdown()
            logger.info("Telegram polling \u2192 detenido")
        except Exception as e:
            logger.warning("Telegram polling \u2192 error al detener: %s", e)'''

assert old in content, "Fragmento no encontrado"
content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK")