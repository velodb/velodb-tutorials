# Superset configuration for VeloDB Integration Lab

import os

# General config
ROW_LIMIT = 5000
SUPERSET_WEBSERVER_PORT = 8088

# Secret key - should be set via environment in production
SECRET_KEY = os.getenv('SUPERSET_SECRET_KEY', 'thisISaSECRET_1234_changeme')

# Database connection for Superset metadata
SQLALCHEMY_DATABASE_URI = 'sqlite:////app/superset_home/superset.db'

# Enable CSRF protection
WTF_CSRF_ENABLED = True

# Cache configuration
CACHE_CONFIG = {
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
}

# Feature flags
FEATURE_FLAGS = {
    'ENABLE_TEMPLATE_PROCESSING': True,
    'DASHBOARD_NATIVE_FILTERS': True,
    'DASHBOARD_CROSS_FILTERS': True,
    'DASHBOARD_NATIVE_FILTERS_SET': True,
    'ALERT_REPORTS': True,
}

# Enable SQL Lab
ENABLE_PROXY_FIX = True

# VeloDB connection settings from environment
VELODB_HOST = os.getenv('VELODB_HOST', 'localhost')
VELODB_PORT = os.getenv('VELODB_PORT', '9030')
VELODB_USER = os.getenv('VELODB_USER', 'admin')
VELODB_PASSWORD = os.getenv('VELODB_PASSWORD', '')
VELODB_DATABASE = os.getenv('VELODB_DATABASE', 'user_analytics')

# Construct VeloDB connection string
VELODB_URI = f"mysql+pymysql://{VELODB_USER}:{VELODB_PASSWORD}@{VELODB_HOST}:{VELODB_PORT}/{VELODB_DATABASE}"

# Add VeloDB as a default database connection
SQLALCHEMY_EXAMPLES_URI = VELODB_URI

# Logging
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
LOG_LEVEL = 'INFO'

# Timeout settings for long-running queries
SUPERSET_WEBSERVER_TIMEOUT = 300
SQLLAB_TIMEOUT = 300
SQLLAB_VALIDATION_TIMEOUT = 120

# Allow embedding dashboards
PUBLIC_ROLE_LIKE = "Gamma"
SESSION_COOKIE_SAMESITE = "Lax"

# Enable async queries
SQLLAB_ASYNC_TIME_LIMIT_SEC = 600
