-- Dashboard KPIs (Last 30 Days)
SELECT
    (SELECT COUNT(DISTINCT user_id) FROM fact_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS active_users,
    (SELECT COUNT(*) FROM fact_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_events,
    (SELECT COUNT(DISTINCT session_id) FROM fact_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_sessions,
    (SELECT COUNT(*) FROM fact_conversions WHERE conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_conversions,
    (SELECT ROUND(SUM(revenue), 0) FROM fact_conversions WHERE conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS total_revenue
