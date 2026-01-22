#!/usr/bin/env python3
"""
Setup VeloDB Customer Analytics Dashboard in Superset.
Creates datasource, datasets, and provides explore links.
"""

import os
import sys
import time
import requests
import json
from urllib.parse import quote_plus

SUPERSET_URL = "http://localhost:8088"
ADMIN_USER = os.environ.get("SUPERSET_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")

# VeloDB connection details from environment
VELODB_HOST = os.environ.get("VELODB_HOST", "localhost")
VELODB_PORT = os.environ.get("VELODB_PORT", "9030")
VELODB_USER = os.environ.get("VELODB_USER", "root")
VELODB_PASSWORD = os.environ.get("VELODB_PASSWORD", "")
VELODB_DATABASE = os.environ.get("VELODB_DATABASE", "user_analytics")


def get_session():
    """Get authenticated session with Superset."""
    session = requests.Session()
    session.get(f"{SUPERSET_URL}/login/")
    session.post(f"{SUPERSET_URL}/login/",
                 data={"username": ADMIN_USER, "password": ADMIN_PASSWORD},
                 allow_redirects=True)

    csrf_resp = session.get(f"{SUPERSET_URL}/api/v1/security/csrf_token/")
    if csrf_resp.status_code == 200:
        csrf_token = csrf_resp.json().get("result")
        session.headers.update({"X-CSRFToken": csrf_token})

    session.headers.update({"Content-Type": "application/json"})
    return session


def create_database(session):
    """Create VeloDB database connection."""
    print("[SETUP] Creating VeloDB database connection...")

    encoded_password = quote_plus(VELODB_PASSWORD)
    sqlalchemy_uri = f"mysql://{VELODB_USER}:{encoded_password}@{VELODB_HOST}:{VELODB_PORT}/{VELODB_DATABASE}"

    payload = {
        "database_name": "VeloDB",
        "engine": "mysql",
        "sqlalchemy_uri": sqlalchemy_uri,
        "expose_in_sqllab": True,
        "allow_run_async": True,
        "allow_ctas": False,
        "allow_cvas": False,
    }

    resp = session.post(f"{SUPERSET_URL}/api/v1/database/", json=payload)
    if resp.status_code in [200, 201]:
        db_id = resp.json().get("id")
        print(f"[SETUP] Database created with ID: {db_id}")
        return db_id
    elif "already exists" in resp.text.lower():
        resp = session.get(f"{SUPERSET_URL}/api/v1/database/?q=(filters:!((col:database_name,opr:eq,value:VeloDB)))")
        if resp.status_code == 200:
            result = resp.json().get("result", [])
            if result:
                db_id = result[0]["id"]
                print(f"[SETUP] Database already exists with ID: {db_id}")
                return db_id

    print(f"[ERROR] Failed to create database: {resp.text[:200]}")
    return None


def create_physical_dataset(session, db_id, table_name):
    """Create a physical table dataset."""
    payload = {
        "database": db_id,
        "schema": VELODB_DATABASE,
        "table_name": table_name,
    }

    resp = session.post(f"{SUPERSET_URL}/api/v1/dataset/", json=payload)
    if resp.status_code in [200, 201]:
        ds_id = resp.json().get("id")
        print(f"[SETUP] Dataset '{table_name}' created with ID: {ds_id}")
        return ds_id
    elif "already exists" in resp.text.lower():
        resp = session.get(f"{SUPERSET_URL}/api/v1/dataset/?q=(filters:!((col:table_name,opr:eq,value:{table_name})))")
        if resp.status_code == 200:
            result = resp.json().get("result", [])
            if result:
                ds_id = result[0]["id"]
                print(f"[SETUP] Dataset '{table_name}' already exists with ID: {ds_id}")
                return ds_id

    print(f"[WARN] Could not create dataset '{table_name}': {resp.text[:100]}")
    return None


def refresh_dataset(session, ds_id):
    """Refresh dataset to sync columns from database."""
    resp = session.put(f"{SUPERSET_URL}/api/v1/dataset/{ds_id}/refresh")
    if resp.status_code == 200:
        print(f"[SETUP] Dataset {ds_id} refreshed")
    return resp.status_code == 200


def create_chart_via_explore(session, ds_id, chart_name, viz_type, form_data):
    """Create chart using the explore endpoint which properly saves query context."""

    # Build the full form_data with datasource info
    full_form_data = {
        "datasource": f"{ds_id}__table",
        "viz_type": viz_type,
        "slice_name": chart_name,
        **form_data
    }

    # Use the explore_json endpoint to validate and get results
    payload = {
        "form_data": json.dumps(full_form_data)
    }

    # Save the chart via the save endpoint
    save_payload = {
        "action": "saveas",
        "slice_name": chart_name,
        "form_data": json.dumps(full_form_data),
    }

    resp = session.post(
        f"{SUPERSET_URL}/superset/explore_json/",
        data={"form_data": json.dumps(full_form_data)},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if resp.status_code == 200:
        # Now save the slice
        save_resp = session.post(
            f"{SUPERSET_URL}/superset/save_or_overwrite_slice/",
            data={
                "form_data": json.dumps(full_form_data),
                "action": "saveas",
                "slice_name": chart_name,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if save_resp.status_code == 200:
            result = save_resp.json()
            chart_id = result.get("form_data", {}).get("slice_id")
            if chart_id:
                print(f"[SETUP] Chart '{chart_name}' created with ID: {chart_id}")
                return chart_id

    print(f"[WARN] Could not create chart '{chart_name}'")
    return None


def create_simple_dashboard(session, title):
    """Create an empty dashboard that users can populate."""
    payload = {
        "dashboard_title": title,
        "slug": "velodb-analytics",
        "published": True,
    }

    resp = session.post(f"{SUPERSET_URL}/api/v1/dashboard/", json=payload)
    if resp.status_code in [200, 201]:
        dash_id = resp.json().get("id")
        print(f"[SETUP] Dashboard '{title}' created with ID: {dash_id}")
        return dash_id
    elif "already exists" in resp.text.lower():
        resp = session.get(f"{SUPERSET_URL}/api/v1/dashboard/?q=(filters:!((col:slug,opr:eq,value:velodb-analytics)))")
        if resp.status_code == 200:
            result = resp.json().get("result", [])
            if result:
                return result[0]["id"]

    print(f"[WARN] Could not create dashboard: {resp.text[:100]}")
    return None


def setup_dashboard():
    """Main setup function."""
    print("=" * 50)
    print("VeloDB Customer Analytics - Superset Setup")
    print("=" * 50)

    # Wait for Superset to be ready
    print("[SETUP] Waiting for Superset to be ready...")
    for i in range(30):
        try:
            resp = requests.get(f"{SUPERSET_URL}/health", timeout=5)
            if resp.status_code == 200:
                print("[SETUP] Superset is ready!")
                break
        except:
            pass
        time.sleep(2)
    else:
        print("[ERROR] Superset not ready after 60 seconds")
        return False

    # Get authenticated session
    print("[SETUP] Authenticating...")
    session = get_session()

    # Create database connection
    db_id = create_database(session)
    if not db_id:
        return False

    # Create physical datasets for each table
    tables = ["dim_users", "dim_features", "dim_campaigns", "fact_events", "fact_conversions"]
    dataset_ids = {}

    for table in tables:
        ds_id = create_physical_dataset(session, db_id, table)
        if ds_id:
            dataset_ids[table] = ds_id
            refresh_dataset(session, ds_id)
        time.sleep(0.3)

    # Create dashboard
    dash_id = create_simple_dashboard(session, "VeloDB User Analytics")

    print("=" * 50)
    print("[SUCCESS] Setup complete!")
    print("")
    print("Access Superset at: http://localhost:8088")
    print("Login: admin / admin")
    print("")
    print("Available datasets:")
    for table, ds_id in dataset_ids.items():
        print(f"  - {table} (ID: {ds_id})")
        print(f"    Explore: http://localhost:8088/explore/?datasource_type=table&datasource_id={ds_id}")
    print("")
    print("SQL Lab: http://localhost:8088/sqllab/")
    print("Dashboard: http://localhost:8088/superset/dashboard/velodb-analytics/")
    print("=" * 50)

    return True


if __name__ == "__main__":
    success = setup_dashboard()
    sys.exit(0 if success else 1)
