# syntax=docker/dockerfile:1.6
# ─────────────────────────────────────────────────────────────
#  CV Tailor — Production Dockerfile (multi-stage, non-root)
# ─────────────────────────────────────────────────────────────

# ── Stage 1: build deps + spaCy model ────────────────────────
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# System deps required for some wheels (lxml, reportlab, pdfplumber image bits)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user -r requirements.txt \
    && python -m spacy download en_core_web_sm

# ── Stage 2: runtime ─────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user (UID 10001 — matches OWASP recommendations)
RUN groupadd --system --gid 10001 app \
    && useradd  --system --uid 10001 --gid app --home /home/app --shell /usr/sbin/nologin app

# Runtime libs only — no build-essential, no compilers
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
        libjpeg62-turbo \
        zlib1g \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages + spaCy model from builder
COPY --from=builder /root/.local /home/app/.local

# Copy application source
COPY --chown=app:app . /app

# Streamlit & app config
ENV PATH=/home/app/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_MAX_UPLOAD_SIZE=5 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    CV_TAILOR_MAX_UPLOAD_BYTES=5242880 \
    CV_TAILOR_MAX_PDF_PAGES=15

# Outputs directory must be user-writable
RUN mkdir -p /app/outputs && chown -R app:app /app/outputs

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app/streamlit_app.py"]
