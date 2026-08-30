# syntax=docker/dockerfile:1
# Stage 1 — build the virtualenv with uv
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Lockfile first, then the dependencies without the project, so this layer is
# keyed only on pyproject.toml/uv.lock and is reused when only sources change.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --extra api

# Sources last, then the project itself into the already-built environment.
# --refresh-package rebuilds from the freshly copied source on every build: the
# version string is stable, so uv would otherwise reuse a stale cached wheel.
COPY aqua_points_calculator ./aqua_points_calculator
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --extra api --refresh-package aqua-points-calculator

# Stage 2 — runtime
FROM python:3.12-slim AS runtime

# No system packages: the calculator is pure Python and the HTTP stack ships wheels.
RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO

USER app
EXPOSE 8000

# The image serves the API by default; the CLI is one `docker run …
# aqua-points-calculator points …` away.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "aqua_points_calculator.api:app", "--host", "0.0.0.0", "--port", "8000"]
