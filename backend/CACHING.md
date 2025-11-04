# Caching

Valkey/Redis cache layer with Airtable webhook invalidation.

## Setup

### 1. Generate Secret
```bash
python -m podium.routers.cache_invalidate
```

### 2. Configure Backend
Add to `.secrets.toml`:
```toml
redis_url = "redis://valkey:6379"
airtable_webhook_secret = "<generated-secret>"
```

### 3. Configure Airtable

**Create "Invalidate Config" table:**
- Fields: `key` (text), `value` (text)
- Records:
  - `webhook_url` → `https://your-backend.com/api/webhooks/airtable`
  - `webhook_secret` → `<paste-generated-secret>`

**Generate ready-to-paste scripts:**
```bash
python -m podium.cache.generate_automation_scripts
# Creates cache/generated/{users,events,projects,votes,referrals}_automation.js
```

**Create 5 automations** (Users, Events, Projects, Votes, Referrals):
1. Trigger: "When record is created or updated" → Select table
2. Action: "Run a script" → Copy from `cache/generated/{table}_automation.js`
3. Click "+ Add input variable(s)": `recordId` → Record ID from Step 1
4. Test and enable

### 4. Schedule Daily Sweep

**Coolify Scheduled Task:**
- Name: Cache Sweep
- Schedule: `0 2 * * *`
- Command: `uv run python -m podium.cache.sweep`

## Usage

### Read Operations
```python
from podium.cache import get_event, get_project, get_user
from podium.db.event import Event

event = get_event(event_id, model=Event)  # Cache-first, 1-5ms, type-safe
```

### Delete Operations
```python
from podium.cache import delete_event, delete_project

delete_event(event_id)  # Deletes Airtable + invalidates cache + tombstone
```

**Always use `cache.delete_*()`, never `db.*.delete()`.**

## How It Works

**Read**: Cache (1-5ms) → Miss: Airtable (100-500ms) → Store in cache (8hr TTL)  
**Write**: Airtable → Automation webhook → Cache updated  
**Delete**: `cache.delete_*()` → Airtable deleted → Cache invalidated → Tombstone set  
**Sweep**: Scan Redis references → Check orphans only → 90% fewer API calls

## Performance

- Cache hit: 1-5ms (100x faster)
- Airtable calls: 80-95% reduction
- Sweep efficiency: 90%+ API savings via reference checking

## Troubleshooting

**"Redis connection failed"**  
→ Check `redis_url` in `.secrets.toml`, verify Valkey running

**Stale data after deletion**  
→ Use `cache.delete_*()` functions, not `db.*.delete()`

**"recordId not configured" in Airtable**  
→ Add input variable in "Run a script" action

**Empty results after restart**  
→ Normal, cache warms up as requests arrive
