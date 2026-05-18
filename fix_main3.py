content = open('app/main.py', 'r', encoding='utf-8').read()

old = 'from app.telegram.polling import start_polling, stop_polling'
new = 'from app.telegram.polling import start_polling, stop_polling\nfrom app.telegram.handler import set_main_loop'

assert old in content, 'IMPORT NO ENCONTRADO'
content = content.replace(old, new)

old2 = '    # Telegram polling\n    import asyncio\n    asyncio.ensure_future(start_polling())'
new2 = '    # Telegram polling\n    import asyncio\n    set_main_loop(asyncio.get_event_loop())\n    asyncio.ensure_future(start_polling())'

assert old2 in content, 'BLOQUE NO ENCONTRADO'
content = content.replace(old2, new2)

open('app/main.py', 'w', encoding='utf-8').write(content)
print('OK - main.py actualizado con set_main_loop')