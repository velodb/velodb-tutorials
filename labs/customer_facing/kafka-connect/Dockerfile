#
# Kafka Connect with Doris Sink Connector for VeloDB
#
# This image extends Confluent's Kafka Connect with the Apache Doris
# Kafka connector, enabling streaming data from Kafka to VeloDB Cloud.
#

FROM confluentinc/cp-kafka-connect:7.5.0

# Install the Doris Kafka Connector
# Using the official Apache Doris Kafka connector from Maven Central
RUN mkdir -p /opt/connectors/doris-kafka-connector && \
    curl -fSL https://repo1.maven.org/maven2/org/apache/doris/doris-kafka-connector/1.0.0/doris-kafka-connector-1.0.0.jar \
    -o /opt/connectors/doris-kafka-connector/doris-kafka-connector-1.0.0.jar

# Copy the sink connector configuration
COPY doris-sink.json /opt/connectors/

# Create startup script that registers the connector after Connect starts
RUN echo '#!/bin/bash\n\
# Wait for Kafka Connect to be ready\n\
echo "Waiting for Kafka Connect to start..."\n\
while ! curl -s http://localhost:8083/connectors > /dev/null 2>&1; do\n\
    sleep 5\n\
done\n\
echo "Kafka Connect is ready"\n\
\n\
# Check if connector already exists\n\
if curl -s http://localhost:8083/connectors/velodb-user-events-sink > /dev/null 2>&1; then\n\
    echo "Connector already exists, skipping registration"\n\
else\n\
    echo "Registering Doris sink connector..."\n\
    # Substitute environment variables in the config\n\
    envsubst < /opt/connectors/doris-sink.json > /tmp/doris-sink-resolved.json\n\
    curl -X POST http://localhost:8083/connectors \\\n\
        -H "Content-Type: application/json" \\\n\
        -d @/tmp/doris-sink-resolved.json\n\
    echo "Connector registered"\n\
fi\n\
' > /opt/connectors/register-connector.sh && chmod +x /opt/connectors/register-connector.sh

# Install envsubst for variable substitution
USER root
RUN yum install -y gettext && yum clean all
USER appuser

# The connector will be registered via the startup script
# Run: docker exec kafka-connect /opt/connectors/register-connector.sh
