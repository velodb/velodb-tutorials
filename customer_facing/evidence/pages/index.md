---
title: User Behavior Analytics Dashboard
---

# User Behavior Analytics

Powered by **[VeloDB](https://docs.velodb.io)** - Real-time analytics with live data streaming.

Data refreshes automatically every 5 seconds.

---

## Key Metrics (Last 30 Days)

```sql kpis
SELECT * FROM velodb.kpis
```

<Grid cols=5>
    <BigValue data={kpis} value=active_users title="Active Users"/>
    <BigValue data={kpis} value=total_events title="Total Events" fmt=num0k/>
    <BigValue data={kpis} value=total_sessions title="Sessions" fmt=num0k/>
    <BigValue data={kpis} value=total_conversions title="Conversions" fmt=num0k/>
    <BigValue data={kpis} value=total_revenue fmt=usd0k title="Revenue"/>
</Grid>

---

## Live Activity (Last 24 Hours)

```sql hourly_activity
SELECT * FROM velodb.hourly_activity
```

<AreaChart
    data={hourly_activity}
    x=hour
    y={['events', 'sessions']}
    title="Hourly Events & Sessions (Updates Every 30s)"
/>

---

## User Activity Trend

```sql daily_activity
SELECT * FROM velodb.daily_activity
```

<LineChart
    data={daily_activity}
    x=activity_date
    y={['users', 'sessions']}
    title="Daily Active Users & Sessions"
/>

---

## Activity by Plan

```sql activity_by_plan
SELECT * FROM velodb.activity_by_plan
```

<AreaChart
    data={activity_by_plan}
    x=activity_date
    y=users
    series=plan
    title="Daily Users by Plan"
/>

---

## Top 10 Features by Usage

```sql top_features
SELECT * FROM velodb.top_features
```

<BarChart
    data={top_features}
    x=feature_name
    y=total_uses
    title="Top Features"
    swapXY=true
/>

---

## Feature Adoption by Plan

```sql feature_adoption
SELECT * FROM velodb.feature_adoption
```

<Heatmap
    data={feature_adoption}
    x=plan
    y=feature_name
    value=uses
    title="Feature Usage: Plan x Feature"
/>

---

## User Journey Flow

```sql sankey_data
SELECT * FROM velodb.sankey_data
```

<SankeyDiagram
    data={sankey_data}
    sourceCol=source
    targetCol=target
    valueCol=value
    title="User Journey: Channel → Feature → Conversion"
/>

---

## Conversion Attribution

```sql attribution
SELECT * FROM velodb.attribution
```

<DataTable data={attribution} rows=20/>

---

## 🔴 Live Revenue Feed

```sql recent_conversions
SELECT * FROM velodb.recent_conversions
```

<DataTable
    data={recent_conversions}
    rows=10
    rowNumbers=false
>
    <Column id=conversion_time title="Time" />
    <Column id=email title="User" />
    <Column id=conversion_type title="Type" />
    <Column id=revenue title="Revenue" fmt=usd />
    <Column id=channel title="Channel" />
</DataTable>

---

*Dashboard powered by VeloDB + Evidence. For auto-refresh, visit [/live.html](/live.html).*
