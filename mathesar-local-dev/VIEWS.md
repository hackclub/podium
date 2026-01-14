# Mathesar Configuration

## Record Summaries

By default, Mathesar may show unhelpful columns (like `airtable_id`) in linked record views. Configure each table's **Record Summary Template** to show meaningful data:

1. Open the table (e.g., Events)
2. Click **Table** tab in the right inspector panel
3. Set **Record Summary Template** to the desired column (e.g., `{name}`)

Recommended settings:
- **Events**: `{name}`
- **Projects**: `{name}`
- **Users**: `{display_name}` or `{email}`

---

## Views

Custom database views for Airtable-like display.

## users_with_events

Shows users with their attending and owned events as array columns.

### Create via Postgres client

Mathesar doesn't have a built-in SQL runner. Use psql, pgAdmin, DBeaver, or similar:

```sql
CREATE VIEW users_with_events AS
SELECT 
    u.id,
    u.email,
    u.display_name,
    u.first_name,
    u.last_name,
    COALESCE(array_agg(DISTINCT att_e.name) FILTER (WHERE att_e.name IS NOT NULL), '{}') AS attending_events,
    COALESCE(array_agg(DISTINCT own_e.name) FILTER (WHERE own_e.name IS NOT NULL), '{}') AS owned_events
FROM users u
LEFT JOIN event_attendees ea ON ea.user_id = u.id
LEFT JOIN events att_e ON att_e.id = ea.event_id
LEFT JOIN events own_e ON own_e.owner_id = u.id
GROUP BY u.id;
```

After creating, refresh Mathesar's schema page—the view appears as a read-only table.

### Drop

```sql
DROP VIEW IF EXISTS users_with_events;
```

---

## Explorations (Alternative)

If you don't want to create a DB view, use Mathesar's **Explorations** feature:

1. Click **Open Data Explorer** (or **+ New Exploration**)
2. Select `users` as base table
3. Add columns and join related tables
4. Save the exploration for reuse

