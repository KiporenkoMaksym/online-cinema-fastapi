import os

from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "online_cinema",
    broker=os.getenv(
        "CELERY_BROKER_URL",
        "redis://127.0.0.1:6379/0",
    ),
    backend=os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://127.0.0.1:6379/1",
    ),
    include=["src.tasks.cleanup"],
)

celery_app.conf.update(
    timezone="UTC",
    beat_schedule={
        "cleanup-expired-activation-tokens": {
            "task": "src.tasks.cleanup.delete_expired_activation_tokens",
            "schedule": crontab(minute=0),
        },
    },
)

celery_app.loader.import_default_modules()
