#!/bin/sh
set -e

echo "=============================================="
echo " TicketingGenie Auth Service — Starting up"
echo "=============================================="

echo "[entrypoint] Running database initializer (tables + seed data)..."
python init_db.py

echo "[entrypoint] Database ready. Starting Auth Service..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload