# PostgreSQL Query Patterns Reference

## Table of Contents
1. [Aggregation Recipes](#1-aggregation-recipes)
2. [Window Functions](#2-window-functions)
3. [CTEs and Subquery Patterns](#3-ctes-and-subquery-patterns)
4. [Time-Based Filtering](#4-time-based-filtering)
5. [Index Maintenance](#5-index-maintenance)
6. [EXPLAIN Interpretation Guide](#6-explain-interpretation-guide)

---

## 1. Aggregation Recipes

### ROAS and Ad Metrics

```sql
-- Campaign-level ROAS for last 30 days
SELECT
  c.name                                               AS campaign,
  SUM(f.impressions)                                   AS impressions,
  SUM(f.clicks)                                        AS clicks,
  ROUND(SUM(f.clicks)::NUMERIC / NULLIF(SUM(f.impressions), 0) * 100, 2) AS ctr_pct,
  SUM(f.spend)                                         AS spend,
  SUM(f.revenue)                                       AS revenue,
  ROUND(SUM(f.revenue) / NULLIF(SUM(f.spend), 0), 2)  AS roas,
  ROUND(SUM(f.spend) / NULLIF(SUM(f.clicks), 0), 4)   AS cpc
FROM fact_ad_performance f
JOIN dim_campaign c ON c.id = f.campaign_id
WHERE f.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY c.id, c.name
ORDER BY roas DESC NULLS LAST;
```

### Revenue by Cohort (signup month)

```sql
SELECT
  DATE_TRUNC('month', u.created_at)::DATE  AS cohort_month,
  DATE_TRUNC('month', o.created_at)::DATE  AS order_month,
  COUNT(DISTINCT u.id)                     AS users,
  SUM(o.amount)                            AS revenue
FROM users u
JOIN orders o ON o.user_id = u.id
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Percentile Distribution

```sql
SELECT
  campaign_id,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY roas) AS median_roas,
  PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY roas) AS p90_roas,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY roas) AS p99_roas
FROM fact_ad_performance
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY campaign_id;
```

### Funnel Conversion Rates

```sql
WITH funnel AS (
  SELECT
    COUNT(*) FILTER (WHERE event_type = 'page_view')   AS views,
    COUNT(*) FILTER (WHERE event_type = 'add_to_cart') AS carts,
    COUNT(*) FILTER (WHERE event_type = 'purchase')    AS purchases
  FROM events
  WHERE occurred_at >= NOW() - INTERVAL '30 days'
)
SELECT
  views,
  carts,
  purchases,
  ROUND(carts::NUMERIC   / NULLIF(views, 0) * 100, 2)    AS view_to_cart_pct,
  ROUND(purchases::NUMERIC / NULLIF(carts, 0) * 100, 2)  AS cart_to_purchase_pct
FROM funnel;
```

---

## 2. Window Functions

### Running Total

```sql
SELECT
  date,
  campaign_id,
  spend,
  SUM(spend) OVER (
    PARTITION BY campaign_id
    ORDER BY date
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS cumulative_spend
FROM fact_ad_performance
ORDER BY campaign_id, date;
```

### 7-Day Rolling Average

```sql
SELECT
  date,
  campaign_id,
  revenue,
  ROUND(AVG(revenue) OVER (
    PARTITION BY campaign_id
    ORDER BY date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ), 2) AS revenue_7d_avg
FROM fact_ad_performance
ORDER BY campaign_id, date;
```

### Rank Within Group

```sql
SELECT
  campaign_id,
  date,
  revenue,
  RANK() OVER (PARTITION BY campaign_id ORDER BY revenue DESC) AS revenue_rank
FROM fact_ad_performance
WHERE date >= CURRENT_DATE - INTERVAL '30 days';
```

### Period-over-Period Comparison (LAG)

```sql
SELECT
  date,
  campaign_id,
  revenue,
  LAG(revenue, 7) OVER (PARTITION BY campaign_id ORDER BY date) AS revenue_7d_ago,
  ROUND(
    (revenue - LAG(revenue, 7) OVER (PARTITION BY campaign_id ORDER BY date))
    / NULLIF(LAG(revenue, 7) OVER (PARTITION BY campaign_id ORDER BY date), 0) * 100,
    2
  ) AS pct_change_7d
FROM fact_ad_performance;
```

---

## 3. CTEs and Subquery Patterns

### Prefer CTEs for Readability, Not Performance

PostgreSQL 12+ materializes CTEs only when they contain side effects or are referenced multiple times. Use CTEs to clarify steps, not to force materialization.

```sql
WITH
  recent_performance AS (
    SELECT campaign_id, SUM(spend) AS spend, SUM(revenue) AS revenue
    FROM fact_ad_performance
    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY campaign_id
  ),
  campaign_roas AS (
    SELECT
      campaign_id,
      spend,
      revenue,
      ROUND(revenue / NULLIF(spend, 0), 2) AS roas
    FROM recent_performance
  )
SELECT c.name, r.spend, r.revenue, r.roas
FROM campaign_roas r
JOIN dim_campaign c ON c.id = r.campaign_id
WHERE r.roas > 2.0
ORDER BY r.roas DESC;
```

### Top-N per Group

```sql
-- Top 3 campaigns by revenue per platform (last 30 days)
SELECT *
FROM (
  SELECT
    platform_id,
    campaign_id,
    SUM(revenue) AS revenue,
    ROW_NUMBER() OVER (PARTITION BY platform_id ORDER BY SUM(revenue) DESC) AS rn
  FROM fact_ad_performance
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
  GROUP BY platform_id, campaign_id
) ranked
WHERE rn <= 3;
```

---

## 4. Time-Based Filtering

### Canonical Patterns

```sql
-- Last N days (inclusive of today)
WHERE date >= CURRENT_DATE - INTERVAL '30 days'

-- Last N days (exclusive of today — for complete days only)
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
  AND date < CURRENT_DATE

-- Current month to date
WHERE date >= DATE_TRUNC('month', CURRENT_DATE)

-- Specific month
WHERE DATE_TRUNC('month', date) = '2024-03-01'

-- Last N hours (timestamp)
WHERE created_at >= NOW() - INTERVAL '24 hours'

-- Between two dates (user-supplied)
WHERE date BETWEEN $1 AND $2  -- $1 and $2 are DATE parameters
```

### Timezone-Aware Filtering

```sql
-- Filter in a specific timezone (AT TIME ZONE)
WHERE created_at AT TIME ZONE 'America/New_York' >= '2024-01-01'

-- Truncate to day in user's timezone
DATE_TRUNC('day', created_at AT TIME ZONE 'America/New_York')
```

**Common mistake:** Comparing a `TIMESTAMPTZ` column with `CURRENT_DATE` causes an implicit cast that may miss rows in non-UTC timezones. Use `NOW()` or cast explicitly.

---

## 5. Index Maintenance

### Check for Missing Indexes (Sequential Scans on Large Tables)

```sql
SELECT
  schemaname,
  relname                   AS table_name,
  seq_scan,
  seq_tup_read,
  idx_scan,
  n_live_tup                AS live_rows
FROM pg_stat_user_tables
WHERE n_live_tup > 100000
  AND seq_scan > idx_scan
ORDER BY seq_tup_read DESC;
```

### Check Index Usage

```sql
SELECT
  indexrelname  AS index_name,
  idx_scan      AS times_used,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;
-- Low idx_scan indexes are candidates for removal
```

### Check Index Bloat

```sql
SELECT
  relname     AS table_name,
  indexrelname AS index_name,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;
```

Rebuild a bloated index without locking:
```sql
REINDEX INDEX CONCURRENTLY idx_fact_campaign_date;
```

---

## 6. EXPLAIN Interpretation Guide

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) <your query>;
```

### Node Types and Their Meaning

| Node | Meaning |
|---|---|
| `Seq Scan` | Full table scan — acceptable only for very small tables |
| `Index Scan` | Uses index to find rows, then fetches heap pages |
| `Index Only Scan` | All needed columns in index — most efficient |
| `Bitmap Heap Scan` | Batch heap access after bitmap index scan — good for range scans |
| `Hash Join` | Builds hash table on smaller relation — good for equality joins |
| `Merge Join` | Requires sorted inputs — fast when both sides already sorted |
| `Nested Loop` | OK for small outer result; expensive if outer is large |

### Spotting Problems

```
Seq Scan on fact_ad_performance (cost=0.00..584123.00 rows=40000000 ...)
                                                            ^^^^^^^^^^
                                                     Planner expected 40M rows — add index or partition
```

```
actual rows=1 loops=12000
              ^^^^^
              Nested loop ran 12000 times — add index on inner join column
```

```
Buffers: shared read=50000
                     ^^^^^
                     50000 * 8KB = 400MB read from disk — consider adding index
```

### Force/Test an Index

```sql
-- Temporarily disable sequential scans to test if index would be used
SET enable_seqscan = off;
EXPLAIN (ANALYZE) SELECT ...;
SET enable_seqscan = on;  -- always reset after testing
```
