# syntax=docker/dockerfile:1.7
FROM golang:1.25.5-bookworm AS alpaca-cli
ARG ALPACA_CLI_VERSION=v0.0.13
RUN CGO_ENABLED=0 go install github.com/alpacahq/cli/cmd/alpaca@${ALPACA_CLI_VERSION}

FROM ghcr.io/astral-sh/uv:0.12.3 AS uv

FROM python:3.12.12-slim-bookworm AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini
RUN uv sync --frozen --no-dev

FROM python:3.12.12-slim-bookworm AS runtime
ENV PATH="/app/.venv/bin:${PATH}" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
COPY --from=alpaca-cli /go/bin/alpaca /usr/local/bin/alpaca
USER app
EXPOSE 8000
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
