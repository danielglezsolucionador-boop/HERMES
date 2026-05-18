import asyncio
from app.telegram.client import validate_connection, send_message

async def main():
    print("Validando conexión...")
    ok = await validate_connection()
    if ok:
        print("✅ Bot conectado")
        sent = await send_message("🟢 Hermes conectado. Subfase 2.1 operacional.")
        print("✅ Mensaje enviado" if sent else "❌ Error enviando mensaje")
    else:
        print("❌ Conexión fallida")

asyncio.run(main())