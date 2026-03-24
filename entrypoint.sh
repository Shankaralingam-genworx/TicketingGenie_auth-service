#!/bin/bash
set -e

# Start Celery worker in background
celery -A src.core.celery.celery_app worker \
  --loglevel=info \
  -Q auth_email \
  --concurrency=2 &

# Start FastAPI
exec uvicorn src.main:app --host 0.0.0.0 --port 8001