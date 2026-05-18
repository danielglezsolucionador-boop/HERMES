content = open('app/telegram/handler.py', 'r', encoding='utf-8').read()

old = '''    await send_message(
        "✅ Hermes activo\n📡 Telegram conectado\n🗄️ DB operacional",
        chat_id=update.message.chat_id,
    )'''

new = '''    await send_message(
        "Hermes activo | Telegram conectado | DB operacional",
        chat_id=update.message.chat_id,
    )'''

old2 = '''    await send_message(
        "🟢 Hermes operacional. Listo para recibir instrucciones.",
        chat_id=update.message.chat_id,
    )'''

new2 = '''    await send_message(
        "Hermes operacional. Listo para recibir instrucciones.",
        chat_id=update.message.chat_id,
    )'''

content = content.replace(old, new)
content = content.replace(old2, new2)
open('app/telegram/handler.py', 'w', encoding='utf-8').write(content)
print('OK - emojis removidos')