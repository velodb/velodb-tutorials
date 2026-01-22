-- Sankey: Channel -> Top Feature -> Conversion (JOIN: 4 tables)
WITH conversion_data AS (
    SELECT
        camp.channel,
        f.feature_name,
        c.conversion_type,
        COUNT(*) AS conversions
    FROM fact_conversions c
    JOIN dim_campaigns camp ON c.campaign_id = camp.campaign_id
    JOIN dim_features f ON c.feature_id = f.feature_id
    WHERE c.conversion_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    GROUP BY camp.channel, f.feature_name, c.conversion_type
),
top_features AS (
    SELECT feature_name
    FROM conversion_data
    GROUP BY feature_name
    ORDER BY SUM(conversions) DESC
    LIMIT 5
)
SELECT
    channel AS source,
    feature_name AS target,
    SUM(conversions) AS value
FROM conversion_data
WHERE feature_name IN (SELECT feature_name FROM top_features)
GROUP BY channel, feature_name

UNION ALL

SELECT
    feature_name AS source,
    conversion_type AS target,
    SUM(conversions) AS value
FROM conversion_data
WHERE feature_name IN (SELECT feature_name FROM top_features)
GROUP BY feature_name, conversion_type
