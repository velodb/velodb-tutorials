-- Feature Adoption by Plan (JOIN: fact_events + dim_users + dim_features)
SELECT
    u.plan,
    f.feature_name,
    COUNT(DISTINCT e.user_id) AS users,
    COUNT(*) AS uses
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
JOIN dim_features f ON e.feature_id = f.feature_id
WHERE e.event_type = 'feature_use'
  AND e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY u.plan, f.feature_name
ORDER BY uses DESC
LIMIT 50
