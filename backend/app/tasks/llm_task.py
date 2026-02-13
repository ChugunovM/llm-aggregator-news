import logging
import requests
from celery import Task
from app.celery_app import celery_app
from app.config import settings
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.repositories.new_repo import create_news_item
from app.utils.telegram_notifier import send_telegram_message

logger = logging.getLogger(__name__)

# Выбираем модель
DEFAULT_MODEL = "mistral:7b-instruct-q4_K_M"

def call_ollama(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.3) -> str:
    """Вызов локального Ollama."""
    ollama_url = f"{settings.OLLAMA_HOST}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 2048
        }
    }
    try:
        resp = requests.post(ollama_url, json=payload, timeout=120)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
        else:
            logger.error(f"Ollama error {resp. status_code}: {resp.text}")
            return ""
    except Exception as e:
        logger.error(f"Ollama request failed: {e}")
        return ""

def is_russian(text: str) -> bool:
    # Простая эвристика: доля кириллических символов
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    return len(text) > 0 and cyrillic / len(text) > 0.3

@celery_app.task(bind=True, max_retries=2)
def process_raw_item(self: Task, item: dict) -> dict:
    """
    Обрабатывает один элемент (пост, статью, сообщение) через LLM.
    """
    title = item.get("title", "")
    text = item.get("text", "")
    source = item.get("source", "unknown")
    url = item.get("url", "")

    if not text.strip():
        return {**item, "processed": False, "reason": "empty_text"}
    
    # Формируем промпт
    prompt = f"""Ты - аналитик новостей. Тебе дан текст на ЛЮБОМ языке.

ЗАДАЧА:
1. Прочитай текст.
2. Сделай краткую суммаризацию на РУССКОМ языке (1-2 предложения).
3. Определи тип события на РУССКОМ: [новость, слух, обзор, критика, пресс-релиз, нейтральное упоминание].
4. Определи тональность на РУССКОМ: [позитивная, нейтральная, негативная].

ВАЖНО:
- Весь ответ ДОЛЖЕН быть на РУССКОМ языке
- Не используй английские слова в JSON-значениях.
- Даже если исходный текст на английском - отвечай ТОЛЬКО по-русски.

Текст: {text[:3000]}

Ответ строго в формате JSON без пояснений:
{{"summary":"...", "event_type": "...", "sentiment": "..."}} 
"""
    try:
        response = call_ollama(prompt)
        if not is_russian(response):
            # Повтор с усилением
            prompt += "\n\nПОВТОРИ ОТВЕТ НА РУССКОМ ЯЗЫКЕ!"
            response = call_ollama(prompt)
        # Извлекаем JSON из ответа (иногда Ollama добавляет markdown)
        import json
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end != -1:
            json_str = response[start:end]
            parsed = json.loads(json_str)
            item.update({
                "summary": parsed.get("summary", ""),
                "event_type": parsed.get("event_type", "unknown"),
                "sentiment": parsed.get("sentiment", "neutral"),
                "processed": True
            })
        else:
            item.update({"processed": False, "error": "invalid_json"})
    except Exception as e:
        logger.error(f"LLM processing failed for {url}: {e}")
        item.update({"processed": False, "error": str(e)})
    
    # сохранить в БД
    db: Session = SessionLocal()
    try:
        # Подготавлчиваем данные для БД
        db_item = {
            "source": item.get("source", "unknown"),
            "company": item.get("company", ""),
            "url": item.get("url", ""),
            "title": item.get("title", ""),
            "raw_text": item.get("text", ""),
            "summary": item.get("summary", ""),
            "event_type": item.get("event_type", ""),
            "sentiment": item.get("sentiment", ""),
            "published_at": item.get("date") or item.get("published"),
            "processed": item.get("processed", True),
        }
        logger.info(f"Saving item with date: {item.get('date')}, published_at: {db_item['published_at']}")
        saved = create_news_item(db, db_item)
        if saved:
            logger.info(f"✅ Saved to DB: {saved.url}")
            message = (
                f"🗞️ <b>{item.get('company')}</b>\n"
                f"{saved.summary or saved.title[:100]}...\n"
                f"<a href='{saved.url}'>Читать</a>"
            )
            send_telegram_message(message)
        else:
            logger.info(f"⏭️ Duplicate skipped: {item.get('url')}")
    except Exception as e:
        logger.error(f"❌ DB save failed for {item.get('url')}: {e}")
    finally:
        db.close()
    
    return item

@celery_app.task
def process_collected_items(results: list, company_name: str) -> dict:
    """
    Получает список результатов от всех задач +название компании и отправляет каждый элемент в LLM.
    """
    logger.info(f"Recieved {len(results)} results for company '{company_name}'")
    logger.info(f"Raw results from group: {results}")
    
    all_items = []
    for result in results:
        logger.info(f"Processing result of type {type(result)}: {len(result) if isinstance(result, (list, tuple)) else 'not a list'} ")
        
        if isinstance(result, list):
            all_items.extend(result)
        else:
            logger.warning(f"Unexpected result type: {type(result)} - skipping")
    
    logger.info(f"Total raw items collected: {len(all_items)}")
    
    # Отправляем каждый элемент в LMM
    for item in all_items:
        # Убедимся, что item - dict
        if isinstance(item, dict):
            process_raw_item.delay(item)
        else:
            logger.warning(f"Skipping non-dict item: {item}")
    
    return {
        "company": company_name,
        "total_raw_items": len(all_items),
        "llm_tasks_submitted": len(all_items),
        "status": "llm_processing_started"
    }