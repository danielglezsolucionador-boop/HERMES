from unittest.mock import MagicMock
from app.telegram.handler import is_authorized
from app.core.config import settings

# Test 1: chat_id autorizado
update_ok = MagicMock()
update_ok.message.chat_id = settings.TELEGRAM_CHAT_ID
result = is_authorized(update_ok)
print(f"✅ Autorizado (esperado True): {result}")
assert result is True

# Test 2: chat_id NO autorizado
update_bad = MagicMock()
update_bad.message.chat_id = 9999999999
result = is_authorized(update_bad)
print(f"✅ Bloqueado (esperado False): {result}")
assert result is False

# Test 3: mensaje None
update_none = MagicMock()
update_none.message = None
result = is_authorized(update_none)
print(f"✅ None bloqueado (esperado False): {result}")
assert result is False

print("\n✅ VALIDACIÓN 2.2 — Seguridad PASSED")