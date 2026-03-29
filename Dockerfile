# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /build

# Enable bytecode compilation for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_PROGRESS=1 \
    PYTHONUNBUFFERED=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (dependencies will be precompiled to .pyc)
# Use cache mount to speed up builds and reduce failures
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy application source
COPY . .

# Sync project (installs the project itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Compile application code to bytecode (.pyc) with optimization level 2
# Note: We compile the application directories but keep .venv completely intact
# This ensures uvicorn and all dependencies work properly
RUN python -m compileall -q -o 2 \
    core/ dao/ db/ model/ routes/ schema/ service/ main.py || true

# Optional: Remove application .py files to reduce size (keep .pyc)
# Keep __init__.py files as they may be needed for package discovery
# Never touch .venv directory
RUN find core/ dao/ db/ model/ routes/ schema/ service/ -type f -name "*.py" \
    ! -name "__init__.py" \
    -delete 2>/dev/null || true

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Reduce image size: no bytecode regeneration, no stdout buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy virtual environment with all dependencies intact
COPY --from=builder /build/.venv /app/.venv

# Copy application bytecode and remaining necessary files
COPY --from=builder /build/core /app/core
COPY --from=builder /build/dao /app/dao
COPY --from=builder /build/db /app/db
COPY --from=builder /build/model /app/model
COPY --from=builder /build/routes /app/routes
COPY --from=builder /build/schema /app/schema
COPY --from=builder /build/service /app/service
COPY --from=builder /build/main.py* /app/
COPY --from=builder /build/static /app/static
COPY --from=builder /build/templates /app/templates

# Create necessary directories
RUN mkdir -p /app/logs /app/data
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
