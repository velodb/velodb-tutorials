# VeloDB RAG Demo - Optimized for size with Alpine
# Stage 1: Build the frontend
FROM node:20-alpine AS frontend-builder

RUN apk add --no-cache git

WORKDIR /frontend
RUN npx -y create-agent-ui@latest app --skip-git \
    && cd app \
    && npm install \
    && npm cache clean --force \
    && rm -rf .git node_modules/.cache

# Stage 2: Final runtime image
FROM python:3.12-alpine

# Install Node.js runtime
RUN apk add --no-cache nodejs npm

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy and install Python dependencies
COPY pyproject.toml ./
COPY src/ ./src/
RUN uv sync --no-dev && rm -rf ~/.cache /root/.cache

# Copy frontend from builder
COPY --from=frontend-builder /frontend/app ./agent-ui

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 7777 3001

ENTRYPOINT ["/entrypoint.sh"]
