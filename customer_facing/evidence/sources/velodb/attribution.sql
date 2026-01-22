-- Conversion Attribution (JOIN: fact_conversions + dim_users + dim_campaigns + dim_features)
SELECT
    camp.channel,
    camp.source,
    f.feature_name,
    c.conversion_type,
    COUNT(*) AS conversions,
    ROUND(SUM(c.revenue), 2) AS revenue
FROM fact_conversions c
JOIN dim_users u ON c.user_id = u.user_id
JOIN dim_campaigns camp ON c.campaign_id = camp.campaign_id
JOIN dim_features f ON c.feature_id = f.feature_id
WHERE c.conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY camp.channel, camp.source, f.feature_name, c.conversion_type
ORDER BY revenue DESC
LIMIT 30
