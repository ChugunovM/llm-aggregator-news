from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base

class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False)
    company = Column(String(100), nullable=False)
    url = Column(Text, nullable=False, unique=True)
    title = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    event_type = Column(String(50), nullable=True)
    sentiment = Column(String(20), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())