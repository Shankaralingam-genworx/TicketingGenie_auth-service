FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first (layer cache)
COPY requirements.txt .

# Install dependencies using uv (no venv — straight to system)
RUN uv pip install --system --no-cache -r requirements.txt

# Copy source code
COPY . .

EXPOSE 8001

# entrypoint.sh runs init_db.py (creates tables + seeds data) then starts uvicorn
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]