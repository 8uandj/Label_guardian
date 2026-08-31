# syntax=docker/dockerfile:1

# ---- Shared system runtime ----
FROM python:3.12-slim AS base

# ---- Stage 1: Build ----
FROM base AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY pyproject.toml README.md ./
# The App Service owns auth, DB, GCS asset streaming and QA workflow. Detector
# execution lives in Dockerfile.inference-service and is reached over HTTP.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install ".[cloud]"

# Application source is copied only into the final image. Keeping it out of the
# dependency layer lets ordinary code changes reuse the expensive CPU inference
# dependency cache.

# ---- Stage 2: Production ----
FROM base AS production

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    INFERENCE_MODE=remote

# Copy the self-contained Python environment from builder.
COPY --from=builder /opt/venv /opt/venv

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Create data directory with correct ownership
RUN mkdir -p /app/data && \
    sed -i 's/\r$//' /app/scripts/start_server.sh && \
    chmod +x /app/scripts/start_server.sh && \
    chown -R appuser:appuser /app/data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://localhost:{os.getenv('PORT', '8000')}/ready\")" || exit 1

CMD ["/app/scripts/start_server.sh"]
