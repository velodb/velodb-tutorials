#!/usr/bin/env python3
"""
Setup VeloDB Customer Analytics Dashboard using Superset's internal ORM models.

Key insight: We pre-define column metadata so charts can render without
needing a live database connection during setup. The columns match the
schema users create in the tutorial.
"""

import os
import sys
import json
from urllib.parse import quote_plus

os.environ.setdefault("SUPERSET_CONFIG_PATH", "/app/superset_config.py")

VELODB_HOST = os.environ.get("VELODB_HOST", "localhost")
VELODB_PORT = os.environ.get("VELODB_PORT", "9030")
VELODB_USER = os.environ.get("VELODB_USER", "root")
VELODB_PASSWORD = os.environ.get("VELODB_PASSWORD", "")
VELODB_DATABASE = os.environ.get("VELODB_DATABASE", "user_analytics")

# Pre-defined schema matching the actual VeloDB tables
TABLE_SCHEMAS = {
    "dim_users": [
        {"column_name": "user_id", "type": "BIGINT", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "email", "type": "VARCHAR(200)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "name", "type": "VARCHAR(100)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "signup_date", "type": "DATE", "is_dttm": True, "groupby": True, "filterable": True},
        {"column_name": "plan", "type": "VARCHAR(20)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "country", "type": "VARCHAR(50)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "industry", "type": "VARCHAR(50)", "is_dttm": False, "groupby": True, "filterable": True},
    ],
    "dim_features": [
        {"column_name": "feature_id", "type": "BIGINT", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "feature_name", "type": "VARCHAR(100)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "category", "type": "VARCHAR(50)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "description", "type": "TEXT", "is_dttm": False, "groupby": False, "filterable": True},
        {"column_name": "tier_required", "type": "VARCHAR(20)", "is_dttm": False, "groupby": True, "filterable": True},
    ],
    "dim_campaigns": [
        {"column_name": "campaign_id", "type": "BIGINT", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "campaign_name", "type": "VARCHAR(100)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "channel", "type": "VARCHAR(50)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "source", "type": "VARCHAR(50)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "medium", "type": "VARCHAR(50)", "is_dttm": False, "groupby": True, "filterable": True},
    ],
    "fact_events": [
        {"column_name": "event_id", "type": "BIGINT", "is_dttm": False, "groupby": False, "filterable": True},
        {"column_name": "user_id", "type": "BIGINT", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "feature_id", "type": "BIGINT", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "campaign_id", "type": "BIGINT", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "session_id", "type": "VARCHAR(50)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "event_type", "type": "VARCHAR(50)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "event_time", "type": "DATETIME", "is_dttm": True, "groupby": True, "filterable": True, "main_dttm_col": True},
        {"column_name": "page_url", "type": "VARCHAR(500)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "search_query", "type": "VARCHAR(200)", "is_dttm": False, "groupby": True, "filterable": True},
    ],
    "fact_conversions": [
        {"column_name": "conversion_id", "type": "BIGINT", "is_dttm": False, "groupby": False, "filterable": True},
        {"column_name": "user_id", "type": "BIGINT", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "feature_id", "type": "BIGINT", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "campaign_id", "type": "BIGINT", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "conversion_type", "type": "VARCHAR(50)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "conversion_time", "type": "DATETIME", "is_dttm": True, "groupby": True, "filterable": True, "main_dttm_col": True},
        {"column_name": "plan_from", "type": "VARCHAR(20)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "plan_to", "type": "VARCHAR(20)", "is_dttm": False, "groupby": True, "filterable": True},
        {"column_name": "revenue", "type": "DECIMAL(10,2)", "is_dttm": False, "groupby": False, "filterable": True},
    ],
}


def main():
    print("=" * 60)
    print("VeloDB Customer Analytics - Dashboard Setup")
    print("=" * 60)

    from superset.app import create_app
    app = create_app()

    with app.app_context():
        from superset import db
        from superset.models.slice import Slice
        from superset.models.dashboard import Dashboard
        from superset.connectors.sqla.models import SqlaTable, TableColumn, SqlMetric
        from superset.models.core import Database
        from superset.utils.core import DatasourceType

        # 1. Create database connection
        print("\n[1/4] Setting up database connection...")
        database = db.session.query(Database).filter_by(database_name="VeloDB").first()

        if not database:
            encoded_password = quote_plus(VELODB_PASSWORD)
            sqlalchemy_uri = f"mysql://{VELODB_USER}:{encoded_password}@{VELODB_HOST}:{VELODB_PORT}/{VELODB_DATABASE}"

            database = Database(
                database_name="VeloDB",
                sqlalchemy_uri=sqlalchemy_uri,
                expose_in_sqllab=True,
                allow_run_async=True,
                allow_ctas=False,
                allow_cvas=False,
            )
            db.session.add(database)
            db.session.commit()
            print(f"       Database 'VeloDB' created (ID: {database.id})")
        else:
            print(f"       Database 'VeloDB' exists (ID: {database.id})")

        # 2. Create datasets with pre-defined columns
        print("\n[2/4] Creating datasets with column metadata...")
        tables = {}

        for table_name, columns in TABLE_SCHEMAS.items():
            tbl = (
                db.session.query(SqlaTable)
                .filter_by(table_name=table_name, schema=VELODB_DATABASE, database_id=database.id)
                .first()
            )

            if not tbl:
                # Find the main datetime column
                main_dttm_col = next(
                    (c["column_name"] for c in columns if c.get("main_dttm_col")),
                    next((c["column_name"] for c in columns if c["is_dttm"]), None)
                )

                tbl = SqlaTable(
                    table_name=table_name,
                    schema=VELODB_DATABASE,
                    database=database,
                    main_dttm_col=main_dttm_col,
                )
                db.session.add(tbl)
                db.session.flush()  # Get the ID

                # Add columns
                for col_def in columns:
                    col = TableColumn(
                        table_id=tbl.id,
                        column_name=col_def["column_name"],
                        type=col_def["type"],
                        is_dttm=col_def["is_dttm"],
                        groupby=col_def["groupby"],
                        filterable=col_def["filterable"],
                    )
                    db.session.add(col)

                # Add common metrics
                count_metric = SqlMetric(
                    table_id=tbl.id,
                    metric_name="count",
                    expression="COUNT(*)",
                    metric_type="count",
                    verbose_name="Row Count",
                )
                db.session.add(count_metric)

                db.session.commit()
                print(f"       {table_name}: created with {len(columns)} columns")
            else:
                print(f"       {table_name}: already exists (ID: {tbl.id})")

            tables[table_name] = tbl

        # Create virtual datasets matching tutorial SQLs
        print("\n       Creating virtual datasets...")

        VIRTUAL_DATASETS = {
            # KPIs - Dashboard summary metrics
            "vw_kpis": {
                "sql": """SELECT
(SELECT COUNT(DISTINCT user_id) FROM fact_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS active_users,
(SELECT COUNT(*) FROM fact_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_events,
(SELECT COUNT(DISTINCT session_id) FROM fact_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_sessions,
(SELECT COUNT(*) FROM fact_conversions WHERE conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_conversions,
(SELECT ROUND(SUM(revenue), 0) FROM fact_conversions WHERE conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_revenue""",
                "columns": [
                    ("active_users", "BIGINT", False),
                    ("total_events", "BIGINT", False),
                    ("total_sessions", "BIGINT", False),
                    ("total_conversions", "BIGINT", False),
                    ("total_revenue", "DECIMAL", False),
                ]
            },
            # Hourly activity for real-time trend
            "vw_hourly_activity": {
                "sql": """SELECT
DATE_FORMAT(event_time, '%Y-%m-%d %H:00:00') AS hour,
COUNT(*) AS events,
COUNT(DISTINCT user_id) AS users,
COUNT(DISTINCT session_id) AS sessions
FROM fact_events
WHERE event_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY DATE_FORMAT(event_time, '%Y-%m-%d %H:00:00')
ORDER BY hour""",
                "columns": [
                    ("hour", "DATETIME", False, True),  # is_dttm=True
                    ("events", "BIGINT", False),
                    ("users", "BIGINT", False),
                    ("sessions", "BIGINT", False),
                ]
            },
            # Daily activity with JOINs
            "vw_daily_activity": {
                "sql": """SELECT
DATE(e.event_time) AS activity_date,
COUNT(DISTINCT e.user_id) AS users,
COUNT(*) AS events,
COUNT(DISTINCT e.session_id) AS sessions
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
JOIN dim_campaigns c ON e.campaign_id = c.campaign_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(e.event_time)
ORDER BY activity_date""",
                "columns": [
                    ("activity_date", "DATE", False, True),
                    ("users", "BIGINT", False),
                    ("events", "BIGINT", False),
                    ("sessions", "BIGINT", False),
                ]
            },
            # Activity by plan
            "vw_activity_by_plan": {
                "sql": """SELECT
DATE(e.event_time) AS activity_date,
u.plan,
COUNT(DISTINCT e.user_id) AS users
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(e.event_time), u.plan
ORDER BY activity_date""",
                "columns": [
                    ("activity_date", "DATE", False, True),
                    ("plan", "VARCHAR(20)", True),
                    ("users", "BIGINT", False),
                ]
            },
            # Top features
            "vw_top_features": {
                "sql": """SELECT
f.feature_name,
COUNT(*) AS total_uses,
COUNT(DISTINCT e.user_id) AS unique_users
FROM fact_events e
JOIN dim_features f ON e.feature_id = f.feature_id
WHERE e.event_type = 'feature_use'
AND e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY f.feature_name
ORDER BY total_uses DESC
LIMIT 10""",
                "columns": [
                    ("feature_name", "VARCHAR(50)", True),
                    ("total_uses", "BIGINT", False),
                    ("unique_users", "BIGINT", False),
                ]
            },
            # Feature adoption heatmap (top 5 features for clean presentation)
            "vw_feature_heatmap": {
                "sql": """SELECT
f.feature_name,
u.plan,
COUNT(*) as usage_count
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
JOIN dim_features f ON e.feature_id = f.feature_id
WHERE f.feature_id IN (
    SELECT feature_id FROM (
        SELECT feature_id, COUNT(*) as cnt
        FROM fact_events
        GROUP BY feature_id
        ORDER BY cnt DESC
        LIMIT 5
    ) top_features
)
GROUP BY f.feature_name, u.plan""",
                "columns": [
                    ("feature_name", "VARCHAR(100)", True),
                    ("plan", "VARCHAR(20)", True),
                    ("usage_count", "BIGINT", False),
                ]
            },
            # Conversion sankey flow
            "vw_conversion_sankey": {
                "sql": """WITH conversion_data AS (
    SELECT
        camp.channel,
        f.feature_name,
        c.conversion_type,
        COUNT(*) AS conversions
    FROM fact_conversions c
    JOIN dim_campaigns camp ON c.campaign_id = camp.campaign_id
    JOIN dim_features f ON c.feature_id = f.feature_id
    WHERE c.conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    GROUP BY camp.channel, f.feature_name, c.conversion_type
),
top_features AS (
    SELECT feature_name
    FROM conversion_data
    GROUP BY feature_name
    ORDER BY SUM(conversions) DESC
    LIMIT 5
)
SELECT
    channel AS source,
    feature_name AS target,
    SUM(conversions) AS value
FROM conversion_data
WHERE feature_name IN (SELECT feature_name FROM top_features)
GROUP BY channel, feature_name

UNION ALL

SELECT
    feature_name AS source,
    conversion_type AS target,
    SUM(conversions) AS value
FROM conversion_data
WHERE feature_name IN (SELECT feature_name FROM top_features)
GROUP BY feature_name, conversion_type""",
                "columns": [
                    ("source", "VARCHAR(100)", True),
                    ("target", "VARCHAR(100)", True),
                    ("value", "BIGINT", False),
                ]
            },
            # Conversion attribution
            "vw_attribution": {
                "sql": """SELECT
camp.channel,
camp.source,
f.feature_name,
c.conversion_type,
COUNT(*) AS conversions,
ROUND(SUM(c.revenue), 2) AS revenue
FROM fact_conversions c
JOIN dim_users u ON c.user_id = u.user_id
JOIN dim_campaigns camp ON c.campaign_id = camp.campaign_id
JOIN dim_features f ON c.feature_id = f.feature_id
WHERE c.conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY camp.channel, camp.source, f.feature_name, c.conversion_type
ORDER BY revenue DESC
LIMIT 30""",
                "columns": [
                    ("channel", "VARCHAR(20)", True),
                    ("source", "VARCHAR(30)", True),
                    ("feature_name", "VARCHAR(50)", True),
                    ("conversion_type", "VARCHAR(20)", True),
                    ("conversions", "BIGINT", False),
                    ("revenue", "DECIMAL", False),
                ]
            },
        }

        for ds_name, ds_config in VIRTUAL_DATASETS.items():
            existing = db.session.query(SqlaTable).filter_by(
                table_name=ds_name, database_id=database.id
            ).first()
            if existing:
                print(f"       {ds_name}: exists (ID: {existing.id})")
                tables[ds_name] = existing
                continue

            ds = SqlaTable(
                table_name=ds_name,
                database=database,
                schema=VELODB_DATABASE,
                sql=ds_config["sql"].strip(),
            )
            db.session.add(ds)
            db.session.flush()

            for col_def in ds_config["columns"]:
                col_name = col_def[0]
                col_type = col_def[1]
                is_groupby = col_def[2]
                is_dttm = col_def[3] if len(col_def) > 3 else False
                db.session.add(TableColumn(
                    table_id=ds.id, column_name=col_name,
                    type=col_type, groupby=is_groupby, filterable=True, is_dttm=is_dttm,
                ))

            db.session.commit()
            print(f"       {ds_name}: created (ID: {ds.id})")
            tables[ds_name] = ds

        # 3. Create charts with complete params
        print("\n[3/4] Creating charts...")

        # Helper to create metric definition
        def sql_metric(expr, label):
            return {"expressionType": "SQL", "sqlExpression": expr, "label": label}

        def simple_metric(col_name, aggregate="SUM"):
            return {"expressionType": "SIMPLE", "column": {"column_name": col_name}, "aggregate": aggregate, "label": col_name}

        charts_config = [
            # === KPI Big Numbers (LARGE fonts for presentation) ===
            {
                "slice_name": "Active Users (30d)",
                "viz_type": "big_number_total",
                "datasource_id": tables["vw_kpis"].id,
                "params": {
                    "metric": simple_metric("active_users", "MAX"),
                    "subheader": "",
                    "header_font_size": 0.6,
                    "subheader_font_size": 0.15,
                    "y_axis_format": ",.2s",
                },
            },
            {
                "slice_name": "Total Events (30d)",
                "viz_type": "big_number_total",
                "datasource_id": tables["vw_kpis"].id,
                "params": {
                    "metric": simple_metric("total_events", "MAX"),
                    "subheader": "",
                    "header_font_size": 0.6,
                    "y_axis_format": ",.2s",
                },
            },
            {
                "slice_name": "Total Sessions (30d)",
                "viz_type": "big_number_total",
                "datasource_id": tables["vw_kpis"].id,
                "params": {
                    "metric": simple_metric("total_sessions", "MAX"),
                    "subheader": "",
                    "header_font_size": 0.6,
                    "y_axis_format": ",.2s",
                },
            },
            {
                "slice_name": "Conversions (30d)",
                "viz_type": "big_number_total",
                "datasource_id": tables["vw_kpis"].id,
                "params": {
                    "metric": simple_metric("total_conversions", "MAX"),
                    "subheader": "",
                    "header_font_size": 0.6,
                    "y_axis_format": ",.2s",
                },
            },
            {
                "slice_name": "Revenue (30d)",
                "viz_type": "big_number_total",
                "datasource_id": tables["vw_kpis"].id,
                "params": {
                    "metric": simple_metric("total_revenue", "MAX"),
                    "subheader": "",
                    "header_font_size": 0.6,
                    "y_axis_format": "$,.0f",
                },
            },
            # === Hourly Activity Line Chart ===
            {
                "slice_name": "Hourly Activity (24h)",
                "viz_type": "echarts_timeseries_line",
                "datasource_id": tables["vw_hourly_activity"].id,
                "params": {
                    "x_axis": "hour",
                    "time_grain_sqla": "PT1H",
                    "metrics": [simple_metric("events", "SUM"), simple_metric("users", "SUM")],
                    "groupby": [],
                    "row_limit": 100,
                    "rich_tooltip": True,
                    "show_legend": True,
                },
            },
            # === Daily Activity Area Chart ===
            {
                "slice_name": "Daily Activity (30d)",
                "viz_type": "echarts_area",
                "datasource_id": tables["vw_daily_activity"].id,
                "params": {
                    "x_axis": "activity_date",
                    "time_grain_sqla": "P1D",
                    "metrics": [simple_metric("events", "SUM"), simple_metric("sessions", "SUM"), simple_metric("users", "SUM")],
                    "groupby": [],
                    "row_limit": 100,
                },
            },
            # === Activity by Plan - Stacked Area ===
            {
                "slice_name": "Activity by Plan",
                "viz_type": "echarts_area",
                "datasource_id": tables["vw_activity_by_plan"].id,
                "params": {
                    "x_axis": "activity_date",
                    "time_grain_sqla": "P1D",
                    "groupby": ["plan"],
                    "metrics": [simple_metric("users", "SUM")],
                    "row_limit": 200,
                    "stack": True,
                },
            },
            # === Top 10 Features - Horizontal Bar (clean, readable) ===
            {
                "slice_name": "Top 10 Features",
                "viz_type": "echarts_timeseries_bar",
                "datasource_id": tables["vw_top_features"].id,
                "params": {
                    "x_axis": "feature_name",
                    "metrics": [sql_metric("SUM(total_uses)", "Usage")],
                    "groupby": [],
                    "row_limit": 10,
                    "order_desc": True,
                    "color_scheme": "supersetColors",
                    "show_legend": False,
                    "rich_tooltip": True,
                    "y_axis_format": "SMART_NUMBER",
                    "orientation": "horizontal",
                    "show_value": True,
                    "stack": False,
                    "only_total": True,
                },
            },
            # === Feature Adoption Heatmap (orange scheme, auto margins for label visibility) ===
            {
                "slice_name": "Feature Adoption Heatmap",
                "viz_type": "heatmap",
                "datasource_id": tables["vw_feature_heatmap"].id,
                "params": {
                    "all_columns_x": "plan",
                    "all_columns_y": "feature_name",
                    "metric": sql_metric("SUM(usage_count)", "Usage"),
                    "row_limit": 500,
                    "linear_color_scheme": "schemeOranges",
                    "xscale_interval": 1,
                    "yscale_interval": 1,
                    "canvas_image_rendering": "pixelated",
                    "normalize_across": "y",
                    "left_margin": "auto",  # Auto-calculate to fit feature name labels
                    "bottom_margin": "auto",
                    "show_legend": True,
                    "show_perc": False,
                    "show_values": False,
                    "sort_x_axis": "alpha_asc",
                    "sort_y_axis": "value_desc",
                },
            },
            # === Conversion Flow Sankey ===
            {
                "slice_name": "Conversion Flow",
                "viz_type": "sankey",
                "datasource_id": tables["vw_conversion_sankey"].id,
                "params": {
                    "groupby": ["source", "target"],
                    "metric": sql_metric("SUM(value)", "Flow"),
                    "row_limit": 100,
                    "color_scheme": "supersetColors",
                },
            },
            # === Conversion Attribution Table (clean, presentation-ready) ===
            {
                "slice_name": "Conversion Attribution",
                "viz_type": "table",
                "datasource_id": tables["vw_attribution"].id,
                "params": {
                    "query_mode": "aggregate",
                    "groupby": ["channel", "source", "feature_name", "conversion_type"],
                    "metrics": [
                        sql_metric("SUM(conversions)", "Conversions"),
                        sql_metric("ROUND(SUM(revenue), 0)", "Revenue ($)"),
                    ],
                    "all_columns": [],
                    "percent_metrics": [],
                    "order_desc": True,
                    "row_limit": 25,
                    "page_length": 25,
                    "include_search": False,
                    "show_cell_bars": True,
                    "table_timestamp_format": "smart_date",
                    "color_pn": True,
                    "column_config": {
                        "Revenue ($)": {"d3NumberFormat": "$,.0f"},
                    },
                },
            },
        ]

        slices = []
        for config in charts_config:
            existing = db.session.query(Slice).filter_by(slice_name=config["slice_name"]).first()
            if existing:
                # Update existing chart
                existing.params = json.dumps(config["params"])
                existing.datasource_id = config["datasource_id"]
                slices.append(existing)
                print(f"       {config['slice_name']}: updated")
            else:
                slc = Slice(
                    slice_name=config["slice_name"],
                    viz_type=config["viz_type"],
                    datasource_type=DatasourceType.TABLE,
                    datasource_id=config["datasource_id"],
                    params=json.dumps(config["params"]),
                )
                db.session.add(slc)
                slices.append(slc)
                print(f"       {config['slice_name']}: created")

        db.session.commit()

        # Refresh to get IDs
        slices = db.session.query(Slice).filter(
            Slice.slice_name.in_([c["slice_name"] for c in charts_config])
        ).all()

        # 4. Create dashboard with layout
        print("\n[4/4] Creating dashboard...")

        dash = db.session.query(Dashboard).filter_by(slug="velodb-analytics").first()
        if not dash:
            dash = Dashboard(
                dashboard_title="VeloDB User Analytics",
                slug="velodb-analytics",
                published=True,
            )
            db.session.add(dash)

        dash.slices = slices

        # Build position layout - organized by visualization type
        # Row 1: 5 KPI Big Numbers
        # Row 2: Hourly Activity (real-time, full width)
        # Row 3: Daily Activity | Activity by Plan (split)
        # Row 4: Top Features | Feature Heatmap (split)
        # Row 5: Conversion Flow Sankey (full width)
        # Row 6: Attribution Table (full width)

        # Get slices by name for precise layout control
        slice_by_name = {s.slice_name: s for s in slices}

        position = {
            "DASHBOARD_VERSION_KEY": "v2",
            "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
            "GRID_ID": {
                "type": "GRID",
                "id": "GRID_ID",
                "children": ["ROW-kpis", "ROW-hourly", "ROW-daily", "ROW-features", "ROW-sankey", "ROW-table"],
                "parents": ["ROOT_ID"],
            },
            "HEADER_ID": {
                "id": "HEADER_ID",
                "type": "HEADER",
                "meta": {"text": "VeloDB User Analytics - Real-time Dashboard"},
            },
        }

        def add_chart_to_row(row_id, chart_name, width, height, idx):
            """Helper to add a chart to a row in the layout"""
            slc = slice_by_name.get(chart_name)
            if not slc:
                return
            chart_id = f"CHART-{row_id}-{idx}"
            position[row_id]["children"].append(chart_id)
            position[chart_id] = {
                "type": "CHART",
                "id": chart_id,
                "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {"width": width, "height": height, "chartId": slc.id, "sliceName": slc.slice_name},
            }

        # Row 1: KPIs (compact but readable)
        position["ROW-kpis"] = {
            "type": "ROW", "id": "ROW-kpis", "children": [],
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        kpi_charts = ["Active Users (30d)", "Total Events (30d)", "Total Sessions (30d)", "Conversions (30d)", "Revenue (30d)"]
        kpi_widths = [2, 3, 2, 2, 3]  # Total = 12
        for i, name in enumerate(kpi_charts):
            add_chart_to_row("ROW-kpis", name, kpi_widths[i], 12, i)

        # Row 2: Hourly Activity - TALL for clear Y-axis
        position["ROW-hourly"] = {
            "type": "ROW", "id": "ROW-hourly", "children": [],
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        add_chart_to_row("ROW-hourly", "Hourly Activity (24h)", 12, 28, 0)

        # Row 3: Daily Activity | Activity by Plan - TALL for trends
        position["ROW-daily"] = {
            "type": "ROW", "id": "ROW-daily", "children": [],
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        add_chart_to_row("ROW-daily", "Daily Activity (30d)", 6, 28, 0)
        add_chart_to_row("ROW-daily", "Activity by Plan", 6, 28, 1)

        # Row 4: Top Features | Heatmap - TALL for all items
        position["ROW-features"] = {
            "type": "ROW", "id": "ROW-features", "children": [],
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        add_chart_to_row("ROW-features", "Top 10 Features", 5, 36, 0)
        add_chart_to_row("ROW-features", "Feature Adoption Heatmap", 7, 36, 1)

        # Row 5: Conversion Flow Sankey - TALL for clear flows
        position["ROW-sankey"] = {
            "type": "ROW", "id": "ROW-sankey", "children": [],
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        add_chart_to_row("ROW-sankey", "Conversion Flow", 12, 36, 0)

        # Row 6: Attribution Table
        position["ROW-table"] = {
            "type": "ROW", "id": "ROW-table", "children": [],
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        add_chart_to_row("ROW-table", "Conversion Attribution", 12, 32, 0)

        dash.position_json = json.dumps(position)

        # Dashboard metadata with auto-refresh enabled
        dash.json_metadata = json.dumps({
            "refresh_frequency": 10,  # Auto-refresh every 10 seconds
            "timed_refresh_immune_slices": [],
            "expanded_slices": {},
            "color_scheme": "supersetColors",
            "label_colors": {},
            "shared_label_colors": {},
            "color_scheme_domain": [],
            "cross_filters_enabled": True,
        })

        db.session.commit()

        # Set permissions - admin user must own all assets
        from flask_appbuilder.security.sqla.models import User
        admin = db.session.query(User).filter_by(username="admin").first()
        if admin:
            # Set owner for datasets
            all_tables = db.session.query(SqlaTable).filter(
                SqlaTable.database_id == database.id
            ).all()
            for tbl in all_tables:
                if admin not in tbl.owners:
                    tbl.owners.append(admin)

            # Set owner for charts
            for slc in slices:
                if admin not in slc.owners:
                    slc.owners.append(admin)

            # Set owner for dashboard
            if admin not in dash.owners:
                dash.owners.append(admin)

            db.session.commit()
            print("       Permissions set for admin user")

        print(f"       Dashboard 'VeloDB User Analytics' ready (ID: {dash.id})")

        # Summary
        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print(f"""
Access Superset:
  URL:       http://localhost:8088
  Login:     admin / admin

Dashboard:   http://localhost:8088/superset/dashboard/velodb-analytics/
SQL Lab:     http://localhost:8088/sqllab/

Charts created: {len(slices)}
  - 5 KPI cards (Active Users, Events, Sessions, Conversions, Revenue)
  - 1 Hourly Activity line chart (24h real-time trend)
  - 1 Daily Activity area chart (30d trend)
  - 1 Activity by Plan stacked area chart
  - 1 Top 10 Features horizontal bar chart
  - 1 Feature Adoption Heatmap
  - 1 Conversion Flow Sankey diagram
  - 1 Conversion Attribution table

Auto-refresh: Enabled (10 seconds)
""")
        print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
