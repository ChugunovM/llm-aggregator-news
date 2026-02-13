from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Interval
from sqlalchemy.sql import func
from app.database import Base
import json

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(100), nullable=False)
    urls = Column(Text, nullable=True)
    telegram_channels = Column(Text, nullable=True)
    interval_hours = Column(Integer, default=2)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    since = Column(DateTime(timezone=True), nullable=True)

    def get_urls(self) -> list:
        return json.loads(self.urls) if self.urls else []
    
    def get_telegram_channels(self) -> list:
        return json.loads(self.telegram_channels) if self.telegram_channels else []
    
    def set_urls(self, urls: list):
        self.urls = json.dumps(urls)

    def set_telegram_channels(self, channels: list):
        self.telegram_channels = json.dumps(channels)