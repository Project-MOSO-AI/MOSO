# MOSO AI — Production Dockerfile
# Multi-stage build: builder (compile) → runtime (minimal)

# ── Stage 1: Builder ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

COPY moso_core/requirements-docker.txt ./

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip setuptools wheel

# Core dependencies
RUN pip install --no-cache-dir -r requirements-docker.txt

# API server
RUN pip install --no-cache-dir fastapi uvicorn[standard]

# ── Stage 2: Runtime ──────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="MOSO AI" \
      description="MOSO: Privacy-First Adaptive AI Assistant" \
      version="0.2.0"

# Security: non-root user
RUN groupadd -r moso && useradd -r -g moso -m moso

WORKDIR /app

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    libgomp1 \
    libsndfile1 \
    tesseract-ocr \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder --chown=moso:moso /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (models excluded via .dockerignore)
COPY --chown=moso:moso moso_core/ ./moso_core/
COPY --chown=moso:moso backend/ ./backend/
COPY --chown=moso:moso moso_ui/ ./moso_ui/
COPY --chown=moso:moso run.py ./

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MOSO_HOME=/data/moso \
    MOSO_MODEL_PATH=/models

# Create data directories
RUN mkdir -p /data/moso /models && chown -R moso:moso /data /models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

USER moso
EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
