FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RIFTSCALE_ENV=production \
    RIFTSCALE_CACHE_DIR=/tmp/riftscale-cache

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY riot_model /app/riot_model
COPY tools /app/tools
RUN mkdir -p /app/desktop
COPY desktop/lol_high_rank_comparator.py desktop/all-champion-baselines.json /app/desktop/
COPY config /app/config

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /tmp/riftscale-cache \
    && chown -R appuser:appuser /tmp/riftscale-cache
USER appuser

EXPOSE 8080
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
