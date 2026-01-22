-- Activity by Plan (JOIN: fact_events + dim_users)
SELECT
    DATE(e.event_time) AS activity_date,
    u.plan,
    COUNT(DISTINCT e.user_id) AS users
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(e.event_time), u.plan
ORDER BY activity_date
