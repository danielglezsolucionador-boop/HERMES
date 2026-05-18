content = open('app/main.py', 'r', encoding='utf-8').read()

old_import = 'from app.telegram.polling import start_polling'
new_import = 'from app.telegram.polling import start_polling, stop_polling'

assert old_import in content, 'IMPORT NO ENCONTRADO'
content = content.replace(old_import, new_import)

old_shutdown = '    logger.info("HERMES shutting down - goodbye.")'
new_shutdown = '    await stop_polling()\n    logger.info("HERMES shutting down - goodbye.")'

assert old_shutdown in content, 'SHUTDOWN NO ENCONTRADO'
content = content.replace(old_shutdown, new_shutdown)

open('app/main.py', 'w', encoding='utf-8').write(content)
print('OK - main.py actualizado con stop_polling')