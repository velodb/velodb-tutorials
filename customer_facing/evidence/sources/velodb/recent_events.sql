-- Recent events for real-time feed (last 100 events)
SELECT
    e.event_time,
    u.email,
    u.plan,
    f.feature_name,
    e.event_type,
    e.session_id
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
JOIN dim_features f ON e.feature_id = f.feature_id
ORDER BY e.event_time DESC
LIMIT 100
