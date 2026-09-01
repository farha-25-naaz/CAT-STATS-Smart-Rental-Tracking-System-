FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/backend/requirements.txt

COPY backend /app/backend
COPY ml_engine /app/ml_engine

# Pre-train the deterministic demo models while the image is built. GitHub's
# build runner has more startup time and memory than the small Container Apps
# replica. Placeholder Supabase settings are sufficient here: model training
# falls back to the simulator's built-in site coordinates when the remote
# lookup is unavailable. Production credentials are supplied only at runtime.
RUN cd /app/backend \
    && SUPABASE_URL=https://placeholder.supabase.co \
       SUPABASE_KEY=placeholder-build-key \
       python ml_orchestration.py

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/ml_engine/models \
    && chown -R appuser:appuser /app

USER appuser
WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)" || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
