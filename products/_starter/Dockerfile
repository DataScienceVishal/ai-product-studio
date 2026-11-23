# One image for Azure Container Apps: the built React app and the FastAPI backend that serves it (ADR 0002,
# decision 2). Build context is products/_starter. Runs as a non-root user; migrations run as a separate step.
# Base images are pinned by digest; Dependabot (.github/dependabot.yml) proposes refreshes weekly.
FROM node:22-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    TRUST_PROXY_HEADERS=true FRONTEND_DIST=/app/static
WORKDIR /app

COPY backend/requirements.txt ./
# requirements.txt is generated with hashes (uv pip compile --generate-hashes), so every download is verified.
RUN pip install --require-hashes -r requirements.txt

COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY --from=frontend /build/dist ./static

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"
# --no-proxy-headers: uvicorn must not trust X-Forwarded-For (the client can set its leftmost entry).
# The app reads only the rightmost hop, which Azure Container Apps ingress adds (TRUST_PROXY_HEADERS=true).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-server-header"]
