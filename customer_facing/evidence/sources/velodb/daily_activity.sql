-- Daily Activity Trend (JOIN: fact_events + dim_users + dim_campaigns)
SELECT
    DATE(e.event_time) AS activity_date,
    COUNT(DISTINCT e.user_id) AS users,
    COUNT(*) AS events,
    COUNT(DISTINCT e.session_id) AS sessions
FROM fact_events e
JOIN dim_users u ON e.user_id = u.user_id
JOIN dim_campaigns c ON e.campaign_id = c.campaign_id
WHERE e.event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(e.event_time)
ORDER BY activity_date
