# Production-Optimized Dockerfile for MOSO AI
# Multi-stage build with layer caching and minimal runtime image

FROM python:3.11-slim AS builder

WORKDIR /build

# Install only essential build dependencies (layer caches separately)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (cache before code changes)
COPY moso_core/requirements.txt backend/requirements.txt ./

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip to latest
RUN pip install --upgrade pip setuptools wheel

# Install Python packages (split into layers for better caching)
RUN pip install --no-cache-dir \
    pydantic>=2.6.0 \
    numpy>=1.24.0

RUN pip install --no-cache-dir \
    llama-cpp-python>=0.2.60 \
    onnxruntime>=1.17.0 \
    transformers>=4.36.0 \
    tokenizers>=0.15.0

RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    sqlalchemy==2.0.25 \
    asyncpg==0.29.0 \
    redis[hiredis]==5.0.1

RUN pip install --no-cache-dir \
    psutil>=5.9.0 \
    beautifulsoup4>=4.12.0 \
    networkx>=3.0 \
    pytesseract>=0.3.10

# Optional voice/audio (commented for faster builds)
# RUN pip install --no-cache-dir openai-whisper faster-whisper speechbrain

# Stage 2: Runtime — minimal production image
FROM python:3.11-slim

LABEL maintainer="MOSO AI" \
    description="MOSO: Privacy-First Adaptive AI Assistant" \
    version="0.2.0-dev"

# Security: non-root user
RUN groupadd -r moso && useradd -r -g moso moso

WORKDIR /app

# Runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenblas0 \
    libgomp1 \
    libsndfile1 \
    tesseract-ocr \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder (all packages included)
COPY --from=builder --chown=moso:moso /opt/venv /opt/venv

# Copy application
COPY --chown=moso:moso . .

# Environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MOSO_HOME=/app/.moso \
    MODELS_PATH=/app/models

# Setup data directories
RUN mkdir -p $MOSO_HOME models && \
    chown -R moso:moso $MOSO_HOME models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

USER moso
EXPOSE 8000

# Start FastAPI backend
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
