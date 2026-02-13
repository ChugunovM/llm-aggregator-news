from celery import Celery
from app.celery_app import celery_app
from app.tasks.main_workflow import trigger_company_monitoring
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.subscription import Subscription
from datetime import datetime, timedelta

@celery_app.task
def run_due_subscriptions():
    """Запускает все подписки, чей интервал наступил"""
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        subs = db.query(Subscription).filter(
            Subscription.is_active == True,
            (
                (Subscription.last_run_at.is_(None)) |
                (Subscription.last_run_at < now - timedelta(hours=Subscription.interval_hours))
            )
        ).all()

        for sub in subs:
            trigger_company_monitoring.delay(
                company_name=sub.company,
                sources=["rss", "telegram"],
                urls=sub.get_urls(),
                telegram_channels=sub.get_telegram_channels()
            )
            sub.last_run_at = now
            db.commit()
    finally:
        db.close()