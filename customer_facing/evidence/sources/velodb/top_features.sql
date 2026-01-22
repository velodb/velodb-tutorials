-- Top 10 Features by Usage (JOIN: fact_events + dim_features)
SELECT
    f.feature_name,
    COUNT(*) AS total_uses,
    COUNT(DISTINCT e.user_id) AS unique_users
FROM fact_events e
JOIN dim_features f ON e.feature_id = f.feature_id
WHERE e.event_type = 'feature_use'
  AND e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY f.feature_name
ORDER BY total_uses DESC
LIMIT 10
