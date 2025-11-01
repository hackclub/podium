# Event Migration Scripts

This directory contains scripts for migrating events from external Airtable bases into Podium.

## Template Usage

1. **Copy the template**: `cp migrate_events_template.py migrate_my_event.py`

2. **Configure the migration** by editing these sections in your new file:

   ```python
   # Source base configuration
   SOURCE_BASE_ID = "appXXXXXXXXXXXXXX"  # Your external base
   SOURCE_EVENTS_TABLE_ID = "tblXXXXXXXXXXXXXX"
   SOURCE_EVENTS_VIEW_ID = "viwXXXXXXXXXXXXXX"  # Optional

   # Event settings
   EVENT_CONFIG = {
       "feature_flag": "my-event",  # Unique identifier for this event type
       "votable": False,
       "leaderboard_enabled": False,
       "demo_links_optional": True,
   }

   # Field mappings (source field name -> Podium field name)
   FIELD_MAPPINGS = {
       "event_name": "event_name",
       "poc_email": "email",
       # ... add your fields
   }
   ```

3. **Test with dry run**:
   ```bash
   cd backend
   uv run python event_migrations/migrate_my_event.py
   ```

4. **Run for real** (set `TEST_RUN = False` in the script):
   ```bash
   uv run python event_migrations/migrate_my_event.py
   ```

5. **Resume if interrupted**:
   ```bash
   uv run python event_migrations/migrate_my_event.py --resume logs/migration_results_my-event_20251031_123456.json
   ```

## Features

- **Dry run mode**: Test migrations without creating records
- **Resumable**: Pick up where you left off if interrupted
- **Progress tracking**: Saves results after each event
- **Duplicate detection**: Skips events that already exist by slug
- **User management**: Creates or finds users based on email

## Migration Flow

1. Pull events from source Airtable base
2. For each event:
   - Create or find user (event owner) by email
   - Create event in Podium with specified settings
   - Add feature flag to event
   - Save progress
3. Generate summary report

## File Structure

- `migrate_events_template.py` - Generic template (do not modify)
- `migrate_*.py` - Event-specific migration scripts
- `logs/migration_results_*.json` - Migration progress and results

## Example: Daydream Migration

See `../migrate_daydream_events.py` for a full-featured example that includes:
- Attendee migration
- Record verification
- Per-event confirmation
- Complex field mappings
