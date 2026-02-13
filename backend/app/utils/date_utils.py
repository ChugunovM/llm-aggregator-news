import re
from datetime import datetime
from dateparser import parse as parse_date
from urllib.parse import urlparse

def extract_date_from_url(url: str) -> datetime | None:
    """Пытается извлечь дату из URL (например, /2026/01/...)."""
    path = urlparse(url).path
    match = re.search(r'/(\d{4})/(\d{1,2})/', path)
    if match:
        year, month = match.groups()
        try:
            return datetime(int(year), int(month), 1)
        except ValueError:
            pass
    return None

def extract_data_from_html(html_content: str, url: str) -> datetime | None:
    """Извлекает дату из HTML через мета-теги и текст."""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')

    # Извлекаем первые 500 символов всего HTML — часто там дата
    raw_text = soup.get_text()[:500]
    if raw_text:
    # Ищем паттерн вроде "January 29, 2026" в начале текста
        import re
        match = re.search(
            r'\b(?:January|February|March|April|May|June|'
            r'July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b',
            raw_text
        )
        if match:
            try:
                dt = parse_date(match.group(0))
                if dt:
                    return dt
            except:
                pass

    for selector in [
        'meta[property="article:published_time"]',
        'meta[itemprop="datePublished"]',
        'time[datetime]',
        'time[itemprop="datePublished"]'
    ]:
        tag = soup.select_one(selector)
        if tag and tag.get('datetime'):
            try:
                return datetime.fromisoformat(tag['datetime'].replace('Z', '+00:00'))
            except:
                pass
        if tag and tag.get_text(strip=True):
            try:
                dt = parse_date(tag.get_text(strip=True))
                if dt:
                    return dt
            except:
                pass
    
    # Ищем текстовые паттерны ВБЛИЗИ заголовка или в блоках с классами "date", "update", "meta"
    candidates = []

    # Классы, где часто лежит дата
    for cls in ['date', 'pub-date', 'updated', 'meta', 'timestamp', 'byline', 'header-meta']:
        for el in soup.find_all(class_=cls):
            text = el.get_text(strip=True)
            if text:
                candidates.append(text)
    
    # Также ищем рядом с заголовком
    title_el = soup.find(['h1', 'h2'])
    if title_el:
        for sibling in title_el.find_next_siblings(limit=3):
            text = sibling.get_text(strip=True)
            if text:
                candidates.append(text)
    
    # Ищем в теле страницы - первые 3 параграфа
    for p in soup.find_all('p', limit=5):
        text = p.get_text(strip=True)
        if text and any(kw in text.lower() for kw in ['update', 'published', 'released', 'as of']):
            candidates.append(text)
    
    # Парсим все кандидаты чеез dateparser
    for cand in candidates:
        try:
            dt = parse_date(cand, languages=['en', 'ru'], settings={'STRICT_PARSING': False})
            if dt:
                return dt
        except Exception:
            continue

    # 1. Open Graph
    og = soup.find('meta', property='article:published_time')
    if og and og.get('content'):
        try:
            return datetime.fromisoformat(og['content'].replace('Z', '+00:00'))
        except:
            pass
    
    # 2. Schema.org
    schema = soup.find('meta', itemprop='datePublished')
    if schema and schema.get('content'):
        try:
            return datetime.fromisoformat(schema['content'].replace('Z', '+00:00'))
        except:
            pass
    
    # 3. JSON-LD
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            import json
            data = json.loads(script.string)
            if isinstance(data, dict) and 'datePublished' in data:
                return datetime.fromisoformat(data['datePublished'].replace('Z', '+00:00'))
        except:
            continue
    
    # 4.Поиск в основном тексте (последняя надежда)
    text = soup.get_text()
    # Ищем шаблоны вроде "January 29, 2026"
    date_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', text)
    if date_match:
        try:
            return parse_date(date_match.group(0))
        except:
            pass
    
    # 5. Из URL
    return extract_date_from_url(url)