# Module 5: End-to-End Verification

This module validates the complete data pipeline from PostgreSQL through Flink CDC to VeloDB and visualization in Superset.

## Verification Checklist

| Component | Check | Expected |
|-----------|-------|----------|
| PostgreSQL | Tables created, data populated | ✓ 5 tables with seed + generated data |
| Flink CDC | All 5 jobs running | ✓ RUNNING state |
| VeloDB | All tables synced | ✓ Matching row counts |
| Superset | Dashboard displaying data | ✓ Charts render with data |

## Step 1: Verify Docker Services

```bash
# Check all containers are running
docker compose ps

# Expected output:
# NAME        STATUS                   PORTS
# datagen     Up
# flink-cdc   Up                       6123/tcp, 0.0.0.0:8081->8081/tcp
# postgres    Up (healthy)             0.0.0.0:5432->5432/tcp
# superset    Up (healthy)             0.0.0.0:8088->8088/tcp
```

## Step 2: Verify PostgreSQL Source

```bash
# Check PostgreSQL is healthy
docker exec postgres pg_isready -U labuser -d user_analytics

# Check table counts
docker exec postgres psql -U labuser -d user_analytics -c "
SELECT 'dim_users' as table_name, COUNT(*) as rows FROM dim_users
UNION ALL SELECT 'dim_features', COUNT(*) FROM dim_features
UNION ALL SELECT 'dim_campaigns', COUNT(*) FROM dim_campaigns
UNION ALL SELECT 'fact_events', COUNT(*) FROM fact_events
UNION ALL SELECT 'fact_conversions', COUNT(*) FROM fact_conversions
ORDER BY table_name;"
```

Expected output:
```
   table_name    | rows
-----------------+------
 dim_campaigns   |    5
 dim_features    |   10
 dim_users       |   10+  (grows with datagen)
 fact_conversions|   varies
 fact_events     |   varies (grows ~5/sec)
```

## Step 3: Verify Flink CDC Jobs

### Check Job Status

```bash
# Via curl
curl -s http://localhost:8081/jobs/overview | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Job Status:')
print('-' * 50)
for job in data['jobs']:
    name = job['name'].replace('insert-into_default_catalog.default_database.', '')
    print(f\"{job['state']:10} {name}\")"
```

Expected: All 5 jobs show `RUNNING`

### Check via Flink Web UI

Open http://localhost:8081 and verify:
- 5 jobs listed
- All in "RUNNING" state
- Checkpoints completing successfully

### Check Stream Load Activity

```bash
# Look for successful loads
docker logs flink-cdc 2>&1 | grep "Status.*Success" | tail -5

# Check load details
docker logs flink-cdc 2>&1 | grep -A3 "NumberLoadedRows" | tail -12
```

## Step 4: Verify VeloDB Target

### Row Count Comparison

Run in VeloDB SQL Editor or via MySQL client:

```sql
USE user_analytics;

-- Check row counts
SELECT 'dim_users' as tbl, COUNT(*) as cnt FROM dim_users
UNION ALL SELECT 'dim_features', COUNT(*) FROM dim_features
UNION ALL SELECT 'dim_campaigns', COUNT(*) FROM dim_campaigns
UNION ALL SELECT 'fact_events', COUNT(*) FROM fact_events
UNION ALL SELECT 'fact_conversions', COUNT(*) FROM fact_conversions;
```

### Data Freshness Check

```sql
-- Check latest event timestamp
SELECT MAX(event_time) as latest_event FROM fact_events;

-- Should be within seconds of current time
SELECT NOW() as current_time;
```

### Sample Data Verification

```sql
-- Check dimension data
SELECT * FROM dim_users LIMIT 5;
SELECT * FROM dim_features LIMIT 5;
SELECT * FROM dim_campaigns;

-- Check recent events
SELECT * FROM fact_events ORDER BY event_time DESC LIMIT 10;

-- Check recent conversions
SELECT * FROM fact_conversions ORDER BY conversion_time DESC LIMIT 5;
```

## Step 5: Verify Superset

### Access Dashboard

1. Open http://localhost:8088
2. Login with admin/admin
3. Navigate to **Dashboards**

### Check Database Connection

1. Go to **Settings** → **Database Connections**
2. Verify "VeloDB Cloud" connection shows green/healthy
3. Click **Test Connection** to verify

### Run Test Query

1. Go to **SQL Lab**
2. Select database: VeloDB Cloud
3. Run:

```sql
SELECT
    u.plan,
    COUNT(DISTINCT e.user_id) as users,
    COUNT(*) as events
FROM user_analytics.fact_events e
JOIN user_analytics.dim_users u ON e.user_id = u.user_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
GROUP BY u.plan;
```

## Step 6: End-to-End Data Flow Test

### Insert Test Record in PostgreSQL

```bash
docker exec postgres psql -U labuser -d user_analytics -c "
INSERT INTO dim_users (email, name, plan, country, industry)
VALUES ('e2e.test@example.com', 'E2E Test User', 'Enterprise', 'USA', 'Testing')
RETURNING user_id, email;"
```

### Verify in VeloDB (within 10-15 seconds)

```sql
SELECT * FROM user_analytics.dim_users
WHERE email = 'e2e.test@example.com';
```

### Update Test Record

```bash
docker exec postgres psql -U labuser -d user_analytics -c "
UPDATE dim_users SET plan = 'Pro' WHERE email = 'e2e.test@example.com';"
```

### Verify Update in VeloDB

```sql
SELECT email, plan FROM user_analytics.dim_users
WHERE email = 'e2e.test@example.com';
-- Should show plan = 'Pro'
```

## Automated Verification Script

Run the complete verification:

```bash
#!/bin/bash
echo "=== VeloDB Integration Lab Verification ==="
echo ""

# 1. Docker services
echo "1. Checking Docker services..."
docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "NAME|Up"
echo ""

# 2. PostgreSQL
echo "2. Checking PostgreSQL..."
docker exec postgres psql -U labuser -d user_analytics -c "SELECT COUNT(*) as events FROM fact_events;" | tail -3
echo ""

# 3. Flink CDC
echo "3. Checking Flink CDC jobs..."
curl -s http://localhost:8081/jobs/overview | python3 -c "
import sys, json
for job in json.load(sys.stdin)['jobs']:
    print(f\"  {job['state']:10} {job['name'].split('.')[-1]}\")" 2>/dev/null || echo "  Flink not responding"
echo ""

# 4. VeloDB
echo "4. Checking VeloDB connection..."
mysql -h $VELODB_FE_HOST -P 9030 -u $VELODB_USER -p$VELODB_PASSWORD \
  -e "SELECT COUNT(*) as velodb_events FROM user_analytics.fact_events;" 2>/dev/null || echo "  VeloDB connection failed"
echo ""

# 5. Superset
echo "5. Checking Superset..."
curl -s -o /dev/null -w "  HTTP Status: %{http_code}\n" http://localhost:8088/health

echo ""
echo "=== Verification Complete ==="
```

## Troubleshooting

### PostgreSQL Not Healthy

```bash
docker logs postgres | tail -20
docker compose restart postgres
```

### Flink Jobs Not Running

```bash
docker logs flink-cdc 2>&1 | grep -i error | tail -10
docker compose restart flink-cdc
```

### VeloDB Data Not Syncing

1. Check stream load errors:
   ```bash
   docker logs flink-cdc 2>&1 | grep -i "load Result" | tail -5
   ```

2. Verify VeloDB credentials in `.env`

3. Check IP whitelist in VeloDB Cloud Console

### Superset Cannot Query

1. Test database connection in SQL Lab
2. Re-add database connection if needed
3. Check Superset logs:
   ```bash
   docker logs superset | tail -20
   ```

## Performance Metrics

Monitor these metrics for a healthy pipeline:

| Metric | Healthy Value |
|--------|---------------|
| Flink checkpoint interval | 10s |
| Stream load latency | < 5s |
| Events/second throughput | ~5 (configured rate) |
| VeloDB query latency | < 1s |

## Cleanup Test Data

```bash
# Remove test user
docker exec postgres psql -U labuser -d user_analytics -c "
DELETE FROM dim_users WHERE email = 'e2e.test@example.com';"
```

## Summary

If all verification steps pass:

✅ PostgreSQL source is generating data
✅ Flink CDC is capturing and streaming changes
✅ VeloDB is receiving and storing data
✅ Superset can query and visualize data

**Congratulations!** Your real-time data pipeline is working correctly.

## Next Steps

- Explore creating custom dashboards in Superset
- Try modifying the data generation rate in `.env`
- Experiment with VeloDB SQL queries and analytics
- Review the full [TUTORIAL.md](../TUTORIAL.md) for advanced topics
