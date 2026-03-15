"""Celery application factory."""

from celery import Celery

from src.config.settings import settings

celery_app = Celery(
    "auth_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.core.celery.workers.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)