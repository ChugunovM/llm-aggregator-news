from celery import chord
from app.celery_app import celery_app
from app.tasks.rss_task import scrape_rss_or_html
from app.tasks.telegram_task import scrape_telegram_channels
from app.tasks.llm_task import process_collected_items
from datetime import datetime, timezone

@celery_app.task(bind=True)
def trigger_company_monitoring(self, company_name: str, sources: list, urls: list = None, telegram_channels: list = None):
    """
    Основной workflow мониторинга компании.
    """
    task_start_time = datetime.now(timezone.utc).isoformat()
    jobs = []

    # RSS/HTML
    if "rss" in sources and urls:
        jobs.append(scrape_rss_or_html.s(company_name, urls, task_start_time))

    # Telegram
    if "telegram" in sources and telegram_channels:
        jobs.append(scrape_telegram_channels.s(company_name, telegram_channels, task_start_time))

    if not jobs:
        return {"error": "No valid sources provided", "status": "failed"}
    
    # chord: выполнить jobs,затем вызвать callback
    result = chord(jobs)(process_collected_items.s(company_name))

    return {"task_id": result.id, "status": "workflow_started"}