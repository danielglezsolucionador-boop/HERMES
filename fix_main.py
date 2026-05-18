content = open('app/main.py', 'r', encoding='utf-8').read()

# Agregar import de polling
old_import = 'from app.db.engine import engine'
new_import = 'from app.db.engine import engine\nfrom app.telegram.polling import start_polling'

assert old_import in content, 'IMPORT NO ENCONTRADO'
content = content.replace(old_import, new_import)

# Agregar inicio de polling en lifespan después de DB check
old_yield = '    yield'
new_yield = '    # Telegram polling\n    import asyncio\n    asyncio.ensure_future(start_polling())\n    logger.info("  telegram : polling started")\n    yield'

assert old_yield in content, 'YIELD NO ENCONTRADO'
content = content.replace(old_yield, new_yield)

open('app/main.py', 'w', encoding='utf-8').write(content)
print('OK - main.py actualizado con Telegram polling')