FROM flink:1.17.2-java11

# Install required tools
USER root
RUN apt-get update && apt-get install -y \
    curl \
    netcat-openbsd \
    postgresql-client \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Download Flink CDC and Doris connectors
WORKDIR /opt/flink/lib

# Flink CDC PostgreSQL connector (version 3.1.0 per VeloDB docs)
RUN curl -fSL https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-postgres-cdc/3.1.0/flink-sql-connector-postgres-cdc-3.1.0.jar -o flink-sql-connector-postgres-cdc-3.1.0.jar

# Doris/VeloDB Flink connector (use latest version for VeloDB Cloud compatibility)
RUN curl -fSL https://repo1.maven.org/maven2/org/apache/doris/flink-doris-connector-1.17/25.1.0/flink-doris-connector-1.17-25.1.0.jar -o flink-doris-connector-1.17-25.1.0.jar

# Copy job scripts
WORKDIR /opt/flink
COPY start-cdc-job.sh /opt/flink/start-cdc-job.sh
COPY cdc-job.sql /opt/flink/cdc-job.sql
RUN chmod +x /opt/flink/start-cdc-job.sh

USER flink
