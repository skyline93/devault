from __future__ import annotations

from celery import Celery

from devault.settings import get_settings


def make_celery() -> Celery:
    s = get_settings()
    app = Celery(
        "devault",
        broker=s.redis_url,
        backend=s.redis_url,
        include=["devault.worker.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_default_queue="devault",
    )
    return app


celery_app = make_celery()
