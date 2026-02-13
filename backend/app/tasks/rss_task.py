import logging
import feedparser
import requests
from urllib.parse import urljoin, urlparse
from trafilatura import fetch_url, extract
from celery import Task
from app.celery_app import celery_app
from bs4 import BeautifulSoup
from app.utils.date_utils import extract_data_from_html
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.netloc and parsed.scheme)

def extract_artlicle_from_url(article_url: str) -> dict | None:
    """Извлекает заголовок и текст из статьи."""
    try:
        downloaded = fetch_url(article_url)
        if not downloaded:
            return None
        
        # Сначала пробуем trafilatura
        result = extract(
            downloaded,
            include_comments=False,
            only_with_metadata=False,
            url=article_url
        )
        logger.info(f"Trafilatura title: {getattr(result, 'title', None)}")
        logger.info(f"Trafilatura text preview: {getattr(result, 'text', '')[:200]}")
        
        if not result:
            return None

        if isinstance(result, str):
            title = ""
            text = result
        elif hasattr(result, 'title'):
            title = result.title or ""
            text = result.text or ""
        else:
            title = ""
            text = ""
        
        item = {
            "title": str(title).strip(),
            "text": str(text).strip(),
            "url": article_url,
            "date": None
        }

        for key, val in item.items():
            if callable(val):
                logger.error(f"Callable detected in item[{key}]: {val}")

        # Дополнительно: ищем дату в HTML, если trafilatura не нашла
        if not item["date"]:
            published_date = extract_data_from_html(downloaded, article_url)
            if published_date:
                logger.info(f"✅ Date extracted: {published_date} from source: {article_url}")
                item["date"] = published_date.isoformat()
            else:
                logger.warning(f"⚠️ No date found for: {article_url}")

        return item

    except Exception as e:
        logger.warning(f"Failed to extract article {article_url}: {e}")
        return None

@celery_app.task(bind=True, max_retries=2)
def scrape_rss_or_html(self: Task, company_name: str, urls: list, since: str = None) -> list:
    """
    Парсит список URL: сначала как RSS, если не вышло - как HTML.
    """
    flat_urls = flatten_list(urls)
    logger.info(f"📡 Starting RSS/HTML scrape for '{company_name}' from {len(urls)} URLs")
    logger.info(f"Processing URLs: {urls}")
    for i, url in enumerate(urls):
        logger.info(f"  [{i}] type={type(url)}, value={repr(url)}")

    if not isinstance(urls, list):
        logger.error(f"❌ urls is not a list: {type(urls)} = {urls}")
        return []

    results = []
    for url in flat_urls:
        if not isinstance(url, str):
            logger.warning(f"⚠️ Skipping non-string URL: {url} (type: {type(url)})")
            continue
        url = url.strip()
        if not url:
            continue    

    for url in flat_urls:
        rss_url = find_rss_url(url)
        if rss_url:
            logger.info(f"✅ RSS found at {rss_url}, parsing...")
            items = parse_via_rss(rss_url)
        else:
            logger.info(f"🔄 No RSS at {url}, crawling as news site...")
            items = parse_via_html_news_crawler(url, since=since)
        
        # Добавляем метаданные и компанию источника
        for item in items:
            item.update({
                "source": "rss" if rss_url else "html_crawler",
                "company": company_name
            })
        results.extend(items)
    
    logger.info(f"Total items from {company_name}: {len(results)}")
    return results

def find_rss_url(html_url: str) -> str | None:
    """Ищет RSS-ссылку на странице."""
    try:
        resp = requests.get(html_url, timeout=10, headers={'User-Agent': 'news-aggregator'})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Ищем <link rel="alternate" type="application/rss+xml">
        rss_link = soup.find('link', {'type': 'application/rss+xml'})
        if rss_link and rss_link.get('href'):
            rss_url = rss_link['href']
            # Обрабатываем относительные URL
            from urllib.parse import urljoin
            return urljoin(html_url, rss_url)
    except Exception as e:
        logger.warning(f"Failed to detect RSS at {html_url}: {e}")
    return None

def parse_via_rss(rss_url: str, since: str = None) -> list:
    since_dt = None
    if since:
        since_dt = datetime.fromisoformat(since.replace("Z","+00:00"))

    feed = feedparser.parse(rss_url)
    items = []
    for entry in feed.entries:
        pub_date = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        elif entry.get('published'):
            try:
                pub_date = datetime.fromisoformat(entry.published.replace("Z", "+00:00"))
            except:
                pub_date = None
        
        if since_dt and pub_date and pub_date < since_dt:
            continue

        items.append({
            "title": getattr(entry, "title", ""),
            "text": getattr(entry, "summary", "") + " " + getattr(entry, "description", ""),
            "url": getattr(entry, "link", rss_url),
            "published": getattr(entry, "date", None),
        })
    return items

def extract_news_links_from_page(base_url: str) -> list[str]:
    """Извлекает ссылки на отдельные новости со страницы-агрегатора."""
    try:
        resp = requests.get(base_url, timeout=10, headers={'User-Agent': 'news-aggregator'})
        soup = BeautifulSoup(resp.text, 'html.parser')

        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(base_url, href)
            # Фильтруем внешние ссылки
            if base_url in full_url or full_url.startswith(base_url):
                # Эвристика: путь содержит признаки новости
                if any(kw in full_url.lower() for kw in ['/news/', '/press/', '/blog/', '/article/', '/release/']):
                     links.add(full_url)
        return list(links)[:10]     # ограничение для POC
    except Exception as e:
        logger.error(f"Failed to extract news links from {base_url}: {e}")
        return []

def parse_via_html_news_crawler(base_url: str, since: str = None) -> list:
    """Парсит страницу как новостной агрегатор."""
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except Exception as e:
            logger.warning(f"Failed to parse 'since' date: {e}")

    logger.info(f"🔍 No RSS found. Crawling as news page: {base_url}")
    news_links = extract_news_links_from_page(base_url)
    items = []
    for link in news_links:
        article = extract_artlicle_from_url(link)
        if article:
            article_date = None
            if article.get("date"):
                try:
                    article_date = datetime.fromisoformat(article["date"].replace("Z", "+00:00"))
                except Exception as e:
                    logger.debug(f"Date parsing failed for {link}: {e}")    
            
            if since_dt and article_date and article_date < since_dt:
                logger.debug(f"⏭️ Skipping old article ({article_date} < {since_dt}): {link}")
                continue
            
            items.append(article)

    logger.info(f"✅ Found {len(items)} relecant articles (since={since_dt})")
    return items

def flatten_list(nested_list):
    """Преобразует [['a'], ['b', 'c']] -> ['a', 'b', 'c']"""
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result