# aiPHeed API: the final thesis system (FIRI v2, AIPHEED_LEAD2_MODEL=thesis), served by uvicorn.
# Build context is backend/. The SQLite database lives on a mounted disk (DATABASE_URL), never in the image.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libgomp1: LightGBM's OpenMP runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch first, so requirements.txt does not pull the multi-GB CUDA build.
COPY requirements.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.11.0 \
    && pip install -r requirements.txt

COPY . .

ENV AIPHEED_LEAD2_MODEL=thesis \
    AIPHEED_STRICT_MODEL=1 \
    PORT=8000
EXPOSE 8000

# Create or upgrade the database schema on the disk, then serve.
CMD ["sh", "-c", "python -m alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
