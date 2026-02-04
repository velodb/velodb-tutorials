FROM apache/superset:3.1.0

USER root

# Install MySQL driver for VeloDB connectivity
RUN pip install mysqlclient pymysql

# Copy configuration
COPY superset_config.py /app/pythonpath/superset_config.py
COPY init_superset.sh /app/init_superset.sh

RUN chmod +x /app/init_superset.sh

USER superset

# Initialize Superset
RUN superset db upgrade

# Create admin user
RUN superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@example.com \
    --password admin || true

# Initialize roles and permissions
RUN superset init

EXPOSE 8088

CMD ["/app/init_superset.sh"]
