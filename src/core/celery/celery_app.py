from celery import Celery
from src.config.settings import settings

celery_app = Celery(
    "auth_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "src.core.celery.workers.email_tasks",
    ],
)

from src.core.celery.workers import email_tasks

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Optional but recommended
   task_routes = {
    "src.core.celery.workers.email_tasks.*": {"queue": "auth_email"},
},

    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
)