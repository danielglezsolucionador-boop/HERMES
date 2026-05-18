content = open('app/core/config.py', 'r', encoding='utf-8').read()

old = '    # Logging'
new = '    # Telegram\n    TELEGRAM_BOT_TOKEN: str = ""\n    TELEGRAM_CHAT_ID: int = 0\n\n    # Logging'

assert old in content, 'NO ENCONTRADO'
content = content.replace(old, new)
open('app/core/config.py', 'w', encoding='utf-8').write(content)
print('OK - Telegram settings agregados')