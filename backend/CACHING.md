# Caching System

Podium uses Valkey/Redis for caching with Airtable webhook-driven invalidation.

## Quick Start

### 1. Start Valkey
```bash
docker run -d -p 6379:6379 valkey/valkey
```

### 2. Generate Webhook Secret
```bash
python -m podium.routers.cache_invalidate
```

### 3. Configure Backend
Add to `backend/.secrets.toml`:
```toml
redis_url = "redis://localhost:6379"
airtable_webhook_secret = "<generated-secret>"
```

### 4. Configure Airtable

**Create "Invalidate Config" table:**
- Fields: `key` (text), `value` (text)
- Records:
  - key: `webhook_url`, value: `https://your-backend.com/api/webhooks/airtable`
  - key: `webhook_secret`, value: `<paste-generated-secret>`

**Create 5 automations** (Users, Events, Projects, Votes, Referrals):
1. Trigger: When record created/updated
2. Action: Run script (copy from `podium/cache/airtable_automation.js`)
3. Update `TABLE_NAME` constant to match table
4. Test and enable

### 5. Schedule Daily Sweep

**For Coolify:**

1. Go to your Podium service in Coolify
2. Navigate to **Scheduled Tasks**
3. Click **Add Scheduled Task**
4. Configure:
   - **Name**: Cache Sweep
   - **Schedule (cron)**: `0 2 * * *` (runs daily at 2 AM)
   - **Command**: `uv run python -m podium.cache.sweep`
   - **Container**: Use the same container/environment as your main app
5. Save and enable

The task will automatically use the same environment variables and secrets as your main application.

**For local cron (development):**
```bash
0 2 * * * cd /path/to/backend && uv run python -m podium.cache.sweep
```

**Test manually:**
```bash
# In development
uv run python -m podium.cache.sweep

# In Docker
podman run --rm --env-file .env -v $(pwd)/.secrets.toml:/app/.secrets.toml podium-test uv run python -m podium.cache.sweep
```

## How It Works

### Read Flow
```
API request → Cache (1-5ms) → Miss: Airtable (100-500ms) → Store in cache
```

### Write Flow
```
API writes to Airtable → Airtable automation → Webhook updates cache
```

### Delete Flow
```python
from podium.cache import delete_event

delete_event(event_id)  # Deletes from Airtable + invalidates cache + sets tombstone
```

**IMPORTANT:** Always use `cache.delete_*()` functions, never `db.*.delete()` directly.

### Daily Sweep (Reference-Optimized)
```
1. Scan Redis: Extract all referenced IDs (users → events, projects → events, etc.)
2. Find orphans: Cached IDs NOT in referenced set
3. Check Airtable: Only verify suspected orphans (~5-10 requests vs 100+)
4. Clean up: Remove confirmed deletions + set tombstones

Efficiency: 90%+ reduction in Airtable API calls during sweep
```

## Configuration

- **TTL**: 8 hours (configurable in `cache/operations.py::CACHE_TTL_SECONDS`)
- **Tombstone TTL**: 6 hours (prevents repeated 404s)
- **Indices**: Auto-created on startup for slug, email, event, owner, points

## Performance

### Read Performance
- **Cache hit**: ~1-5ms (100x faster than Airtable)
- **Cache miss**: ~100-500ms (same as before, but populates cache)
- **Expected hit rate**: 80-95% after warmup
- **Airtable API reduction**: 80-95% fewer calls

### Sweep Efficiency
- **Traditional approach**: Check every cached record (~100+ Airtable calls)
- **Reference-optimized**: Only check orphans (~5-10 Airtable calls)
- **Efficiency gain**: 90%+ reduction in API calls during sweep

## Troubleshooting

### "Redis connection failed"
- Check Valkey running: `redis-cli ping`
- Verify `redis_url` in `.secrets.toml`

### Stale data after deletion
- Use `cache.delete_*()` functions (not `db.*.delete()`)
- Ensure Airtable automations are enabled
- Check webhook logs for errors
- Worst case: Data expires after 8hrs

### Empty results after restart
- Normal! Cache warms up as users make requests
- Queries automatically fall back to Airtable

## Coolify Deployment Checklist

### Environment Variables
Add to Coolify environment:
```bash
PODIUM_REDIS_URL=redis://valkey:6379  # Or your Valkey service URL
PODIUM_AIRTABLE_WEBHOOK_SECRET=<generated-secret>
```

### Scheduled Task Setup
1. **Service**: Your Podium app
2. **Task Name**: Cache Sweep  
3. **Schedule**: `0 2 * * *`
4. **Command**: `uv run python -m podium.cache.sweep`

### Verification
After deployment:
```bash
# Check Redis connection in logs
# Should see: "✓ Redis/Valkey connection established"
# Should see: "✓ ProjectCache index created" (etc.)

# Test webhook manually
curl -X POST https://your-app.com/api/webhooks/airtable \
  -H "Content-Type: application/json" \
  -H "X-Airtable-Secret: <your-secret>" \
  -d '{"table":"Events","record":{"id":"test"},"record_id":"test","timestamp":"2025-01-01T00:00:00Z"}'
```

## Files Modified

**New:**
- `podium/cache/` - Complete cache layer
- `podium/routers/cache_invalidate.py` - Webhook endpoint

**Updated:**
- `podium/main.py` - Redis init at startup
- `podium/config.py` - Redis settings
- `podium/routers/{users,events,projects}.py` - Cache-first queries
