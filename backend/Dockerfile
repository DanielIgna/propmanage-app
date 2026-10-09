# PropManage backend (FastAPI) — container for Railway.
# Data lives in Supabase (DB_BACKEND=postgres, STORAGE_BACKEND=supabase); the
# /data volume only holds local caches (3D/plan files) and backup archives.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DT_UPLOAD_DIR=/data/uploads/digital_twin \
    HH_UPLOAD_DIR=/data/uploads/house_health \
    BACKUP_DIR=/data/backups

# poppler-utils: PDF plan rendering (pdf2image). Blender / Playwright browsers are optional
# features that degrade gracefully when absent, so they are not installed here.
RUN apt-get update \
 && apt-get install -y --no-install-recommends poppler-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
