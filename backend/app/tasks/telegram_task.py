import os
import logging
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from celery import Task
from app.celery_app import celery_app
from app.config import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SESSION_FILE = os.path.join("data", "telegram.session")

async def _create_client():
    """Создаёт клиент только при необходимости."""
    client = TelegramClient(SESSION_FILE, settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Telegram session not authorized. Run auth_telegram.py first!")
    return client

def is_relevant_to_company(text: str, company: str) -> bool:
    """
    Проверяет, относится ли текст к компании.
    """
    if not text or not company:
        return False
    
    text_lower = text.lower()
    company_lower = company.lower()

    # Базовое совпадение
    if company_lower in text_lower:
        return True
    
    # Синонимы
    synonyms = {
        "apple": ["iphone", "ipad", "macOS","iwatch", "airpods", "mac", "ios", "aapl", "tim cook"],
        "nvidia": ["rtx", "geforce", "cuda", "nvda", "jensen huang"],
        "microsoft": ["windows", "azure", "msft", "satya nadella"],
        "tesla": ["elon musk", "model s", "model 3", "tsla", "cybertruck"],
    }

    for synonym in synonyms.get(company_lower, []):
        if synonym in text_lower:
            return True

    return False

async def _scrape_telegram_channel(channel_username: str, company_name: str, since: str = None, limit: int = 50):
    since_dt = None
    if since:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))

    client = await _create_client()
    messages = []
    try:
        async for message in client.iter_messages(channel_username, limit=limit):
            if not message.message or not message.date:
                continue
            if since_dt and message.date < since_dt:
                break

            text = message.message
            if not is_relevant_to_company(text, company_name):
                continue

            messages.append({
                "text": message.message,
                "url": f"https://t.me/{channel_username}/{message.id}",
                "date": message.date.isoformat(),
                "views": getattr(message, "views", None),  
            })
    except FloodWaitError as e:
        logger.warning(f"Flood wait for {e.seconds} seconds")
        raise
    finally:
        await client.disconnect()
    return messages

@celery_app.task(bind=True)
def scrape_telegram_channels(self: Task, company_name: str, channel_usernames: list, since: str = None) -> dict:
    """
    Собирает последние сообщения из публичных Telegram-каналов.
    """
    import asyncio

    logger.info(f"📨 Scraping Telegram channels for '{company_name}':{channel_usernames}")

    # Инициализация клиента (авторизация один раз)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    all_messages = []
    for username in channel_usernames:
        try:
            msgs = loop.run_until_complete(_scrape_telegram_channel(username, company_name, limit=20))
            for msg in msgs:
                all_messages.append({
                    "source": "telegram",
                    "company": company_name,
                    "title": "",    # в Telegram обычно нет заголовков
                    "text": msg["text"],
                    "url": msg["url"],
                    "date": msg["date"],
                })
        except Exception as e:
            logger.error(f"Failed to scrape @{username}: {e}")
            continue
    
    loop.close()

    return all_messages