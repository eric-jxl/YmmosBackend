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

# Sync project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Compile all Python source files to bytecode (.pyc)
# -b: legacy option for Python 3.5+, writes .pyc next to .py
# -q: quiet mode
# -o: optimization level (0=default, 1=remove asserts, 2=remove docstrings)
# Step 1: Compile all application code to .pyc
# Step 2: Remove .py source files (keep setup.py and exclude .venv)
# Step 3: Compile venv site-packages (if not already compiled by uv)
# Step 4: Remove .py files from site-packages
RUN python -m compileall -b -q -o 2 . && \
    find . -type f -name "*.py" ! -name "setup.py" ! -path "./.venv/*" -delete && \
    python -m compileall -b -q -o 2 .venv/lib/python3.12/site-packages/ || true && \
    find .venv/lib/python3.12/site-packages/ -type f -name "*.py" -delete || true

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Reduce image size: no bytecode regeneration, no stdout buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy virtual environment from builder (only .pyc files)
COPY --from=builder /build/.venv /app/.venv

# Copy application bytecode (only .pyc files, no .py source)
COPY --from=builder /build /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
