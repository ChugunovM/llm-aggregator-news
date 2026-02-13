from http.client import HTTPException
import os
from fastapi import FastAPI, Body
from sqlalchemy.orm import Session
from typing import List
from app.tasks.main_workflow import trigger_company_monitoring
from app.database import Base, engine, SessionLocal
from app.models.subscription import Subscription
from pydantic import BaseModel, validator
from datetime import datetime, timezone

app = FastAPI(title="News Aggregator API", version="0.1.0")

Base.metadata.create_all(bind=engine)

class SubscriptionCreate(BaseModel):
    company: str
    urls: list[str] = []
    telegram_channels: list[str] = []
    interval_hours: int = 2

    @validator('urls', each_item=True)
    def validate_url(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('URL must be a non-empty string')
        return v.strip()

@app.get("/")
def read_root():
    return {"status": "OK", "service": "News Aggregator"}

@app.post("/monitor")
def start_monitoring(
    company: str = Body(..., embed=True),
    urls: List[str] = Body(default=[], embed=True),
    telegram_channels: List[str] = Body(default=[], embed=True),
    sources: List[str] = Body(default=["rss", "telegram"], embed=True)
):
    """
    Запускает фоновую задачу мониторинга компании по выбранным источникам.
    """
    task = trigger_company_monitoring.delay(
        company_name=company,
        sources=sources,
        urls=urls,
        telegram_channels=telegram_channels
    )
    return {
        "message": f"Monitoring started for '{company}'",
        "task_id": task.id,
        "sources": sources,
        "status": "started"
    }

@app.get("/health/ollama")
def check_ollama():
    """
    Проверяет подключение к локальному Ollama.
    """
    import requests
    ollama_host = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
    try:
        resp = requests.get(f"{ollama_host}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return {"status": "ok", "ollama_host": ollama_host, "available_models": models}
        else:
            return {"status": "error", "details": resp.text}
    except Exception as e:
        return {"status": "error", "details": str(e)}
    
@app.post("/subscribe")
def create_subscription(sub: SubscriptionCreate):
    print("✅ Received subscription:", sub.dict())

    db: Session = SessionLocal()
    try:
        new_sub = Subscription(
            company=sub.company,
            interval_hours=sub.interval_hours,
            is_active=True,
            since=datetime.now(timezone.utc)
        )
        new_sub.set_urls(sub.urls)
        new_sub.set_telegram_channels(sub.telegram_channels)
        db.add(new_sub)
        db.commit()
        db.refresh(new_sub)
        return {"id": new_sub.id, "status": "subscribed" }
    finally:
        db.close()

@app.get("/subscriptions")
def list_subscriptions():
    db: Session = SessionLocal()
    try:
        subs = db.query(Subscription).filter(Subscription.is_active == True).all()
        return [
            {
                "id": s.id,
                "company": s.company,
                "urls": s.get_urls(),
                "telegram_channels": s.get_telegram_channels(),
                "interval_hours": s.interval_hours,
                "last_run_at": s.last_run_at,
                "created_at": s.created_at
            }
            for s in subs
        ]
    finally:
        db.close()

@app.delete("/subscribe/{sub_id}")
def delete_subscription(sub_id: int):
    db: Session = SessionLocal()
    try:
        sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
        if sub:
            sub.is_active = False
            db.commit()
            return {"status": "deleted"}
        else:
            raise HTTPException(status_code=404, detail="Subscription not found")
    finally:
        db.close()