FROM node:18-slim

LABEL maintainer="VeloDB"
LABEL description="Customer Analytics Demo - Real-time Data Generator + Evidence Dashboard"

# Install Python and supervisord
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create working directories
WORKDIR /app

# Copy Python datagen
COPY datagen/ /app/datagen/
RUN pip3 install --no-cache-dir --break-system-packages -r /app/datagen/requirements.txt

# Copy Evidence dashboard
COPY evidence/ /app/evidence/
WORKDIR /app/evidence
RUN npm install

# Copy supervisord config and entrypoint
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment variables (defaults)
ENV VELODB_HOST=localhost \
    VELODB_PORT=9030 \
    VELODB_USER=root \
    VELODB_PASSWORD="" \
    VELODB_DATABASE=user_analytics \
    PYTHONUNBUFFERED=1

EXPOSE 3000

WORKDIR /app
ENTRYPOINT ["/app/start.sh"]
