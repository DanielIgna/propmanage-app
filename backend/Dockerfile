# PropManage backend (FastAPI) — container for Railway. Build context = repo root
# (see /.dockerignore): backend code + memory/ and docs/ for the Knowledge Center.
# Data and files live in Supabase (Postgres + Storage); the
# /data volume only holds local caches (3D/plan files) and backup archives.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DT_UPLOAD_DIR=/data/uploads/digital_twin \
    HH_UPLOAD_DIR=/data/uploads/house_health \
    BACKUP_DIR=/data/backups \
    KC_PROJECT_ROOT=/project

# poppler-utils: PDF plan rendering (pdf2image). Blender / Playwright browsers are optional
# features that degrade gracefully when absent, so they are not installed here.
RUN apt-get update \
 && apt-get install -y --no-install-recommends poppler-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY memory /project/memory
COPY docs /project/docs
COPY backend/ .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
