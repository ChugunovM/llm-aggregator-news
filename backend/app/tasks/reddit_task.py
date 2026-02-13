import logging
import time
from datetime import datetime
from typing import List, Optional
from celery import Task
from app.celery_app import celery_app
from app.reddit_client import get_reddit_client
from app.config import settings

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Очистка текста от лишних символов и обрезка до разумного размера."""
    if not text:
        return ""
    # Удаляем переносы, нормализуем пробелы
    text = " ".join(text.split())
    # Ограничиваем длину (LLM не любит очень длинные входы)
    return text[:2000]

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_reddit_for_company(
    self: Task,
    company_name: str,
    subreddits: Optional[List[str]] = None,
    limit_per_sub: int = 10,
    time_filter: str = "week"
) -> dict:
    """
    Парсит Reddit в поисках упоминаний компаний.

    Args:
        company_name: название компании (например, "Tesla")
        subreddits: список сабреддитов, например ["stocks", "technology", "teslamotors"]
                    если None - ищем в r/all
        limit_per_sub: сколько постов брать из каждого сабреддита
        time_filter: за какой период искать
    """
    logger.info(f"🔍 Starting Reddit scrape for '{company_name}' in {subreddits or ['all']}")

    try:
        reddit = get_reddit_client()
        results = []

        targets = subreddits if subreddits else ["all"]

        for subreddit_name in targets:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                # Используем search вместо hot/new - ищем именно по ключевому слову
                submissions = subreddit.search(
                    query=f'"{company_name}"',
                    sort="new",
                    limit=limit_per_sub,
                    time_filter=time_filter
                )

                for post in submissions:
                    # Пропускаем sticky-посты и удалённые
                    if post.stickied or post.removed_by_category:
                        continue

                    item = {
                        "source": "reddit",
                        "company": company_name,
                        "title": clean_text(post.title),
                        "text": clean_text(post.selftext),
                        "url": f"https://reddit.com{post.permalink}",
                        "author": str(post.author) if post.author else "[deleted]",
                        "subreddit": subreddit_name,
                        "score": post.score,
                        "created_utc": datetime.utcfromtimestamp(post.created_utc).isoformat(),
                        "raw_id": post.id,
                    }
                    results.append(item)
                
                # Вежливая пауза между запросами (Reddit может банить за агрессивный парсинг)
                time.sleep(1)
            
            except Exception as sub_e:
                logger.warning(f"⚠️ Error scraping r/{subreddit_name}: {sub_e}")
                continue # не падаем из-за одного сабреддита
        
        logger.info(f"✅ Found {len(results)} Reddit posts for '{company_name}'")

        # TODO: отправить результат на LLM-обработку
        # from .llm_task import process_raw_item
        # for item in results:
        #       process_raw_item.delay(item)

        return {
            "company": company_name,
            "source": "reddit",
            "posts_found": len(results),
            "sample_urls": [r["url"] for r in results[:3]],
            "status": "success"
        }

    except Exception as exc:
        logger.error(f"❌ Fatal error in Reddit scraping: {exc}")
        raise self.retry(exc=exc)