import os

# Superset configuration for VeloDB Customer Analytics Demo

# Secret key for session signing
SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', 'velodb-demo-secret-key-change-in-production')

# SQLite database for Superset metadata (simple, no external DB needed)
SQLALCHEMY_DATABASE_URI = 'sqlite:////app/superset.db'

# Flask app config
WTF_CSRF_ENABLED = False  # Disable CSRF for API access in demo
ENABLE_PROXY_FIX = True

# Authentication - use database auth but with public role having full access
AUTH_TYPE = 1  # AUTH_DB
PUBLIC_ROLE_LIKE = "Admin"  # Give public role admin-like permissions

# Enable embedding
ENABLE_CORS = True
CORS_OPTIONS = {
    'origins': '*',
    'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    'allow_headers': ['*'],
}

# Feature flags
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "EMBEDDED_SUPERSET": True,
}

# Dashboard auto-refresh (in seconds)
DASHBOARD_AUTO_REFRESH_MODE = "fetch"
DASHBOARD_AUTO_REFRESH_INTERVALS = [
    [5, "5 seconds"],
    [10, "10 seconds"],
    [30, "30 seconds"],
    [60, "1 minute"],
    [300, "5 minutes"],
]

# Disable alerts/reports (not needed for demo)
ALERT_REPORTS_NOTIFICATION_DRY_RUN = True

# Disable caching for real-time data
CACHE_CONFIG = {
    'CACHE_TYPE': 'NullCache',
}

DATA_CACHE_CONFIG = {
    'CACHE_TYPE': 'NullCache',
}

# Logging
LOG_LEVEL = 'INFO'
