# Backend image for Azure Container Apps. Runs as a non-root user; migrations run as a separate step.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    TRUST_PROXY_HEADERS=true
WORKDIR /app

COPY requirements.txt ./
# requirements.txt is generated with hashes (uv pip compile --generate-hashes), so every download is verified.
RUN pip install --require-hashes -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"
# --no-proxy-headers: uvicorn must not trust X-Forwarded-For (the client can set its leftmost entry).
# The app reads only the rightmost hop, which Azure Container Apps ingress adds (TRUST_PROXY_HEADERS=true).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
