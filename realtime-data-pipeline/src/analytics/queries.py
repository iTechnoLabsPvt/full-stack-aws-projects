"""
Athena SQL queries for data analytics.
"""

# Hourly event volume
HOURLY_VOLUME = """
SELECT
    date_trunc('hour', timestamp) as hour,
    event_type,
    COUNT(*) as event_count,
    COUNT(DISTINCT user_id) as unique_users
FROM raw_events
WHERE timestamp >= date_add('hour', -24, now())
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC
"""

# Daily active users
DAILY_ACTIVE_USERS = """
SELECT
    date(timestamp) as date,
    COUNT(DISTINCT user_id) as dau,
    COUNT(DISTINCT session_id) as sessions
FROM raw_events
WHERE timestamp >= date_add('day', -30, current_date)
GROUP BY 1
ORDER BY 1 DESC
"""

# Event funnel analysis
FUNNEL_ANALYSIS = """
WITH funnel AS (
    SELECT
        user_id,
        session_id,
        MAX(CASE WHEN event_type = 'page_view' THEN 1 ELSE 0 END) as viewed,
        MAX(CASE WHEN event_type = 'product_view' THEN 1 ELSE 0 END) as product_viewed,
        MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) as added_to_cart,
        MAX(CASE WHEN event_type = 'checkout_started' THEN 1 ELSE 0 END) as checkout_started,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as purchased
    FROM raw_events
    WHERE timestamp >= date_add('day', -7, current_date)
    GROUP BY user_id, session_id
)
SELECT
    COUNT(*) as total_sessions,
    SUM(viewed) as page_views,
    SUM(product_viewed) as product_views,
    SUM(added_to_cart) as add_to_carts,
    SUM(checkout_started) as checkouts,
    SUM(purchased) as purchases,
    ROUND(SUM(purchased) * 100.0 / COUNT(*), 2) as conversion_rate
FROM funnel
"""

# Top events
TOP_EVENTS = """
SELECT
    event_type,
    COUNT(*) as total_events,
    COUNT(DISTINCT user_id) as unique_users,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM raw_events
WHERE timestamp >= date_add('day', -7, current_date)
GROUP BY event_type
ORDER BY total_events DESC
"""

# User engagement
USER_ENGAGEMENT = """
SELECT
    user_id,
    COUNT(*) as event_count,
    COUNT(DISTINCT date(timestamp)) as active_days,
    COUNT(DISTINCT session_id) as sessions,
    MIN(timestamp) as first_seen,
    MAX(timestamp) as last_seen
FROM raw_events
WHERE timestamp >= date_add('day', -30, current_date)
GROUP BY user_id
HAVING COUNT(*) >= 10
ORDER BY event_count DESC
LIMIT 100
"""

# Data quality summary
DATA_QUALITY = """
SELECT
    date_trunc('hour', processed_at) as hour,
    COUNT(*) as total_records,
    SUM(CASE WHEN event_type IS NULL THEN 1 ELSE 0 END) as missing_event_type,
    SUM(CASE WHEN user_id IS NULL OR user_id = '' THEN 1 ELSE 0 END) as missing_user_id,
    SUM(CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END) as missing_timestamp,
    ROUND(
        (COUNT(*) - SUM(CASE WHEN event_type IS NULL THEN 1 ELSE 0 END)) * 100.0 / COUNT(*),
        2
    ) as quality_score
FROM raw_events
WHERE processed_at >= date_add('hour', -24, now())
GROUP BY 1
ORDER BY 1 DESC
"""

QUERIES = {
    "hourly_volume": HOURLY_VOLUME,
    "daily_active_users": DAILY_ACTIVE_USERS,
    "funnel_analysis": FUNNEL_ANALYSIS,
    "top_events": TOP_EVENTS,
    "user_engagement": USER_ENGAGEMENT,
    "data_quality": DATA_QUALITY,
}
