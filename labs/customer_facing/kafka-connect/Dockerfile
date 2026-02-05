#
# Kafka Connect with Doris Sink Connector for VeloDB
#
# This image extends Confluent's Kafka Connect with the Apache Doris
# Kafka connector, enabling streaming data from Kafka to VeloDB Cloud.
#

FROM confluentinc/cp-kafka-connect:7.5.0

# Install the Doris Kafka Connector
# Using the official Apache Doris Kafka connector from Maven Central
USER root
RUN mkdir -p /opt/connectors/doris-kafka-connector && \
    curl -fSL https://repo1.maven.org/maven2/org/apache/doris/doris-kafka-connector/1.0.0/doris-kafka-connector-1.0.0.jar \
    -o /opt/connectors/doris-kafka-connector/doris-kafka-connector-1.0.0.jar

# Install envsubst for variable substitution
RUN yum install -y gettext && yum clean all

# Copy the sink connector configuration
COPY doris-sink.json /opt/connectors/

# Create the auto-registration script
RUN cat > /opt/connectors/register-connector.sh << 'SCRIPT'
#!/bin/bash
# Wait for Kafka Connect to be ready
echo "[Connector Registration] Waiting for Kafka Connect to start..."
MAX_RETRIES=60
RETRY=0
while ! curl -s http://localhost:8083/connectors > /dev/null 2>&1; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "[Connector Registration] ERROR: Kafka Connect not ready after $MAX_RETRIES attempts"
        exit 1
    fi
    sleep 5
done
echo "[Connector Registration] Kafka Connect is ready!"

# Wait a bit more for full initialization
sleep 10

# Check if connector already exists
if curl -s http://localhost:8083/connectors/velodb-kafka-events-sink 2>&1 | grep -q "velodb-kafka-events-sink"; then
    echo "[Connector Registration] Connector already exists, skipping"
else
    echo "[Connector Registration] Registering Doris sink connector..."

    # Substitute environment variables in the config
    envsubst < /opt/connectors/doris-sink.json > /tmp/doris-sink-resolved.json

    echo "[Connector Registration] Config:"
    cat /tmp/doris-sink-resolved.json

    # Register the connector
    RESULT=$(curl -s -X POST http://localhost:8083/connectors \
        -H "Content-Type: application/json" \
        -d @/tmp/doris-sink-resolved.json)

    echo "[Connector Registration] Result: $RESULT"

    # Verify registration
    sleep 5
    STATUS=$(curl -s http://localhost:8083/connectors/velodb-kafka-events-sink/status)
    echo "[Connector Registration] Status: $STATUS"
fi
SCRIPT

RUN chmod +x /opt/connectors/register-connector.sh

# Create startup wrapper that runs Kafka Connect and registers connector
RUN cat > /opt/connectors/startup.sh << 'STARTUP'
#!/bin/bash
# Start the connector registration in background
/opt/connectors/register-connector.sh &

# Execute the original Kafka Connect startup
exec /etc/confluent/docker/run
STARTUP

RUN chmod +x /opt/connectors/startup.sh

USER appuser

# Use our startup wrapper
CMD ["/opt/connectors/startup.sh"]
