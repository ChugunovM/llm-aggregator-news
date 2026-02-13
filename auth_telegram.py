import os
import asyncio
from dotenv import load_dotenv
from telethon.sync import TelegramClient

load_dotenv()

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_FILE = "data/telegram.session"

async def main():
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    print("📞 Авторизация в Telegram...")
    await client.start()
    print("✅ Успешно! Сессия сохранена в data/telegram.session")
    await client().disconnect()

if __name__ == "__main__":
    # Создаём папку, если нет
    os.makedirs("data", exist_ok=True)
    asyncio.run(main())