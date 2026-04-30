---
name: database-postgresql-design
description: "Design efficient PostgreSQL schemas and write optimized queries for analytics workloads. Use when the user needs to: (1) design relational schemas that support fast aggregation and reporting, (2) choose indexing strategies for analytics or time-series data, (3) write aggregation queries for business metrics like ROAS, CTR, or revenue, (4) filter by time windows (last 30 days, month-over-month), (5) diagnose and optimize slow PostgreSQL queries. Triggers on keywords like: schema, index, ROAS, aggregation, GROUP BY, time series, slow query, EXPLAIN, analytics, partitioning, metrics."
---

# Database PostgreSQL Design

Analytics queries must be designed for at schema time — an unindexed 100M-row table cannot be rescued by clever SQL alone.

## Workflow

```
1. Clarify the access pattern (what queries must be fast?)
2. Design the schema to support those patterns
3. Choose indexes to match the WHERE / JOIN / ORDER BY clauses
4. Write the query using efficient patterns
5. Verify with EXPLAIN (ANALYZE, BUFFERS)
```

**Constraint:** State the target access pattern before proposing a schema or index.

---

## 1. Schema Design Decision Tree

```
Data is time-series or append-only AND > 10M rows?
  YES -> Partition by time (RANGE on created_at / date)
  NO  -> Standard normalized table

Need fast analytics aggregations (SUM, COUNT, AVG by dimension)?
  YES -> Add partial indexes on common filter columns
       -> Consider materialized views for pre-aggregated reports
  NO  -> Standard B-tree indexes on FK + filter columns

Many nullable columns or sparse attributes?
  YES -> JSONB column for flexible attributes
  NO  -> Typed columns (prefer NOT NULL with defaults)
```

For detailed schema patterns, see [references/schema-design.md](references/schema-design.md).

---

## 2. Indexing Quick Reference

| Query pattern | Index type |
|---|---|
| Equality filter `WHERE col = $1` | B-tree (default) |
| Range filter `WHERE col BETWEEN $1 AND $2` | B-tree |
| Time-window filter `WHERE created_at >= now() - interval '30 days'` | B-tree on `created_at` (or partition) |
| Partial filter `WHERE status = 'active'` | Partial index: `CREATE INDEX ... WHERE status = 'active'` |
| Multi-column filter `WHERE a = $1 AND b = $2` | Composite index — column order matters (highest selectivity first) |
| Full-text search | GIN index on `tsvector` |
| JSONB key lookup | GIN index on the JSONB column |

**Rule:** Create an index for every column that appears in WHERE, JOIN ON, or ORDER BY for queries running against > 100k rows.

For indexing strategy details and bloat management, see [references/query-patterns.md](references/query-patterns.md).

---

## 3. Analytics Query Patterns

### ROAS (Return on Ad Spend)

```sql
SELECT
  campaign_id,
  SUM(revenue)           AS total_revenue,
  SUM(spend)             AS total_spend,
  ROUND(SUM(revenue) / NULLIF(SUM(spend), 0), 2) AS roas
FROM ad_performance
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY campaign_id
ORDER BY roas DESC;
```

Key patterns:
- `NULLIF(denominator, 0)` — prevents division-by-zero
- Filter on indexed `date` column before aggregation
- Use `CURRENT_DATE - INTERVAL '30 days'` not `NOW()` for date-only columns (avoids timezone cast issues)

### Time-window filtering

```sql
-- Last 30 days (date column)
WHERE date >= CURRENT_DATE - INTERVAL '30 days'

-- Last 30 days (timestamp column)
WHERE created_at >= NOW() - INTERVAL '30 days'

-- Month-to-date
WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)

-- Rolling 7-day window in a window function
SUM(revenue) OVER (
  PARTITION BY campaign_id
  ORDER BY date
  ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
) AS revenue_7d
```

For more aggregation patterns (cohorts, funnels, percentiles), see [references/query-patterns.md](references/query-patterns.md).

---

## 4. Performance Diagnosis

Run this before optimizing any slow query:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT ...;
```

**Read the output — red flags:**

| Signal | Meaning | Fix |
|---|---|---|
| `Seq Scan` on large table | No usable index | Add index on filter column |
| `cost=...rows=1000000` but `actual rows=10` | Stale statistics | `ANALYZE table_name` |
| `Hash Join` with large hash batches | Insufficient `work_mem` | `SET work_mem = '256MB'` for session |
| `Nested Loop` on large outer table | Missing index on inner join column | Add index |
| High `Buffers: shared read` | Cold cache / disk I/O | Check for missing index or large sequential scan |

---

## Resources

- [references/schema-design.md](references/schema-design.md) — Normalization patterns, analytics schema design, partitioning, materialized views
- [references/query-patterns.md](references/query-patterns.md) — Aggregation recipes, window functions, CTEs, index maintenance, EXPLAIN interpretation

## When NOT to Use This Skill

- **Non-relational data models** — for document storage or key-value patterns, consider MongoDB or Redis; PostgreSQL's relational model is overkill
- **Throwaway prototypes** — detailed schema design slows down rapid prototyping; use SQLite or a simple JSON file for early-stage experiments
- **Fully managed cloud databases with auto-schema tools** — if your platform (Supabase, Firebase) handles schema management automatically, this skill adds friction

## Common Mistakes

- Not planning for schema evolution — adding `NOT NULL` columns to existing tables requires backfilling; always plan migration paths before applying constraints
- Using `VARCHAR(255)` for all string fields — choose specific sizes appropriate to the domain (email: 255, phone: 20, UUID: 36); it communicates intent and catches data entry errors
- Neglecting to add indexes during initial design — retroactively adding indexes to large tables requires long-running migrations and table locks

## Related Skills

- [`postgres-k8s-setup`](../postgres-k8s-setup/SKILL.md) — Deploy the designed database to Kubernetes
- [`crm-database-management`](../crm-database-management/SKILL.md) — Apply this design skill to CRM-specific schema needs
- [`backend-rest-api`](../backend-rest-api/SKILL.md) — Build the API layer on top of the designed schema
