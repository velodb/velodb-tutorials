-- Hourly activity for last 24 hours (real-time trend)
SELECT
    DATE_FORMAT(event_time, '%Y-%m-%d %H:00:00') AS hour,
    COUNT(*) AS events,
    COUNT(DISTINCT user_id) AS users,
    COUNT(DISTINCT session_id) AS sessions
FROM fact_events
WHERE event_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY DATE_FORMAT(event_time, '%Y-%m-%d %H:00:00')
ORDER BY hour
