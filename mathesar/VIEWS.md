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

### Create via Mathesar UI

1. Go to **Database** → **Run SQL**
2. Execute:

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

3. Refresh the schema in Mathesar—`users_with_events` appears as a read-only table

### Drop

```sql
DROP VIEW IF EXISTS users_with_events;
```
