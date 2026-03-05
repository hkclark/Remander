FROM python:3.14-slim

# Install uv
ADD https://astral.sh/uv/install.sh /tmp/uv-install.sh
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    sh /tmp/uv-install.sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/* /tmp/uv-install.sh

WORKDIR /app

# Install dependencies (without building the project itself — for Docker layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY src/ src/
COPY migrations/ migrations/

# Now install the project itself
RUN uv sync --frozen --no-dev

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
