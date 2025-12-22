"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from backend.app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "stock_research",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "backend.app.tasks.research",
        "backend.app.tasks.market",
        "backend.app.tasks.funds",
        "backend.app.tasks.etfs",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/New_York",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=540,  # 9 minutes
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # 1 hour
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "market-sentiment-daily": {
        "task": "backend.app.tasks.market.refresh_market_sentiment",
        "schedule": crontab(hour=16, minute=0, day_of_week="1-5"),  # Monday-Friday at 4 PM
    },
    "fund-holdings-check": {
        "task": "backend.app.tasks.funds.check_fund_holdings",
        "schedule": 14400.0,  # Every 4 hours
    },
    "etf-holdings-daily": {
        "task": "backend.app.tasks.etfs.refresh_all_etfs",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    },
}
