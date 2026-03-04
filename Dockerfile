FROM python:3.14-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ src/
COPY migrations/ migrations/

# Create data and logs directories
RUN mkdir -p /app/data /app/logs

# Configurable UID/GID
ARG PUID=1000
ARG PGID=1000
RUN groupadd -g ${PGID} appgroup && \
    useradd -u ${PUID} -g appgroup -m appuser && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "remander.main:app", "--host", "0.0.0.0", "--port", "8000"]
