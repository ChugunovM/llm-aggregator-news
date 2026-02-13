from sqlalchemy.orm import Session
from app.models.news_item import NewsItem
from typing import Optional

def create_news_item(db: Session, item_data: dict) -> Optional[NewsItem]:
    """
    Создаёт запись о новости. Игнорирует дубли по url.
    """
    # Проверяем, существует ли уже
    existing = db.query(NewsItem).filter(NewsItem.url == item_data["url"]).first()
    if existing:
        return None     # дубль
    
    db_item = NewsItem(**item_data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

