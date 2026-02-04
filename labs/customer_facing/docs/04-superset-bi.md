# Module 4: Superset BI Dashboard

This module guides you through setting up Apache Superset to visualize data from VeloDB.

## Architecture

```
VeloDB Cloud (user_analytics)  →  Superset  →  Browser
        ↓                            ↓            ↓
   [dim_users]                  SQL Queries   Dashboards
   [dim_features]               Charts        Real-time
   [dim_campaigns]              Filters       Analytics
   [fact_events]
   [fact_conversions]
```

## Dashboard Preview

![User Analytics Dashboard](./user-analytics-1.png)

The dashboard includes:
- **KPI Cards**: Active Users, Total Events, Sessions, Conversions, Revenue
- **Hourly Activity**: Real-time trend of events and users
- **Daily Activity**: Events, sessions, and users trend (30 days)
- **Activity by Plan**: User activity segmented by subscription tier
- **Top Features**: Most used product features
- **Feature Heatmap**: Feature adoption across plans

## Step 1: Access Superset

Open Superset in your browser:

```
http://localhost:8088
```

Default credentials:
- **Username**: admin
- **Password**: admin

## Step 2: Add VeloDB Database Connection

### Via UI

1. Navigate to **Settings** (gear icon) → **Database Connections**
2. Click **+ Database**
3. Select **MySQL** as the database type
4. Enter connection details:

**Display Name**: `VeloDB Cloud`

**SQLAlchemy URI**:
```
mysql+pymysql://{username}:{password}@{host}:{port}/{database}
```

Example:
```
mysql+pymysql://admin:yourpassword@your-cluster.velodb.io:9030/user_analytics
```

5. Click **Test Connection**
6. If successful, click **Connect**

### Connection String Format

```
mysql+pymysql://admin:VeloDBPassword@lb-xxx.elb.us-east-1.amazonaws.com:9030/user_analytics
```

> **Note**: URL-encode special characters in password (e.g., `@` becomes `%40`)

## Step 3: Create Datasets

Datasets define the tables Superset can query.

### Create Dimension Datasets

1. Navigate to **Data** → **Datasets**
2. Click **+ Dataset**
3. For each dimension table:
   - **Database**: VeloDB Cloud
   - **Schema**: user_analytics
   - **Table**: dim_users / dim_features / dim_campaigns
4. Click **Create Dataset and Create Chart**

### Create Fact Datasets

Repeat for fact tables:
- `fact_events`
- `fact_conversions`

### Create Analytics Virtual Dataset

For pre-aggregated analytics, create a virtual dataset:

1. Go to **SQL Lab** → **SQL Editor**
2. Run this query:

```sql
SELECT
    DATE(e.event_time) as event_date,
    HOUR(e.event_time) as event_hour,
    u.plan,
    u.country,
    f.feature_name,
    f.category as feature_category,
    c.channel as campaign_channel,
    e.event_type,
    COUNT(*) as event_count,
    COUNT(DISTINCT e.user_id) as unique_users,
    COUNT(DISTINCT e.session_id) as sessions
FROM fact_events e
LEFT JOIN dim_users u ON e.user_id = u.user_id
LEFT JOIN dim_features f ON e.feature_id = f.feature_id
LEFT JOIN dim_campaigns c ON e.campaign_id = c.campaign_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
```

3. Click **Save** → **Save as Dataset**
4. Name it: `user_activity_summary`

## Step 4: Create Charts

### KPI: Total Events (Big Number)

1. Go to **Charts** → **+ Chart**
2. Select dataset: `fact_events`
3. Chart type: **Big Number**
4. Metric: `COUNT(*)`
5. Save as "Total Events"

### Events by Hour (Line Chart)

1. Chart type: **Time-series Line Chart**
2. Dataset: `fact_events`
3. Time column: `event_time`
4. Time grain: `hour`
5. Metric: `COUNT(*)`
6. Save as "Hourly Events"

### Events by Plan (Pie Chart)

1. Chart type: **Pie Chart**
2. Dataset: `user_activity_summary`
3. Dimensions: `plan`
4. Metric: `SUM(event_count)`
5. Save as "Events by Plan"

### Top Features (Bar Chart)

1. Chart type: **Bar Chart**
2. Dataset: `user_activity_summary`
3. X-axis: `feature_name`
4. Metric: `SUM(event_count)`
5. Sort: Descending by metric
6. Row limit: 10
7. Save as "Top 10 Features"

### Feature Adoption Heatmap

1. Chart type: **Heatmap**
2. Dataset: `user_activity_summary`
3. X-axis: `plan`
4. Y-axis: `feature_name`
5. Metric: `SUM(unique_users)`
6. Save as "Feature Adoption Heatmap"

### Revenue Summary

1. Chart type: **Big Number with Trendline**
2. Dataset: `fact_conversions`
3. Metric: `SUM(revenue)`
4. Time column: `conversion_time`
5. Save as "Total Revenue"

## Step 5: Create Dashboard

1. Go to **Dashboards** → **+ Dashboard**
2. Name: "User Analytics Dashboard"
3. Drag charts onto the canvas
4. Arrange in a grid layout:

```
┌─────────────────────────────────────────────────────────────┐
│  Active Users  │  Total Events  │  Sessions  │  Revenue    │
├─────────────────────────────────────────────────────────────┤
│                    Hourly Events Chart                      │
├─────────────────────────────────────────────────────────────┤
│      Events by Plan (Pie)     │     Top 10 Features (Bar)  │
├─────────────────────────────────────────────────────────────┤
│              Feature Adoption Heatmap                       │
└─────────────────────────────────────────────────────────────┘
```

5. Click **Save**

## Step 6: Enable Auto-Refresh

1. Open your dashboard
2. Click the **...** menu → **Set auto-refresh interval**
3. Select **10 seconds** or **30 seconds**
4. The dashboard will now update automatically

## Sample Queries for SQL Lab

### User Activity Summary

```sql
SELECT
    u.plan,
    COUNT(DISTINCT e.user_id) as users,
    COUNT(*) as events,
    COUNT(DISTINCT e.session_id) as sessions
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY u.plan
ORDER BY events DESC;
```

### Conversion Funnel

```sql
SELECT
    conversion_type,
    COUNT(*) as conversions,
    SUM(revenue) as total_revenue,
    AVG(revenue) as avg_revenue
FROM fact_conversions
WHERE conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY conversion_type
ORDER BY conversions DESC;
```

### Feature Usage by Plan

```sql
SELECT
    u.plan,
    f.feature_name,
    f.tier_required,
    COUNT(*) as usage_count
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
JOIN dim_features f ON e.feature_id = f.feature_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY u.plan, f.feature_name, f.tier_required
ORDER BY u.plan, usage_count DESC;
```

## Troubleshooting

### Cannot Connect to VeloDB

1. Check VeloDB IP whitelist includes Superset container's IP
2. Verify credentials are correct
3. Test connection via SQL Lab first

### Charts Show No Data

1. Check dataset is properly configured
2. Verify time range filters
3. Run query in SQL Lab to debug

### Slow Dashboard Loading

1. Create materialized views in VeloDB for complex queries
2. Add filters to reduce data scanned
3. Use aggregated virtual datasets

## Next Steps

**[Module 5: End-to-End Verification](./05-verification.md)** - Validate the complete pipeline
