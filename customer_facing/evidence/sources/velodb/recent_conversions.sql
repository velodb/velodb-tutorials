-- Recent conversions for real-time feed
SELECT
    c.conversion_time,
    u.email,
    u.plan,
    c.conversion_type,
    c.revenue,
    camp.campaign_name,
    camp.channel
FROM fact_conversions c
JOIN dim_users u ON c.user_id = u.user_id
JOIN dim_campaigns camp ON c.campaign_id = camp.campaign_id
ORDER BY c.conversion_time DESC
LIMIT 50
