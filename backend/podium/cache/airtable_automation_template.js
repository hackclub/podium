/**
 * Airtable Automation: {{TABLE_NAME}}
 * 
 * Auto-generated - DO NOT EDIT MANUALLY
 * Edit: backend/podium/cache/airtable_automation_template.js
 * Generate: python -m podium.cache.generate_automation_scripts
 * 
 * SETUP:
 * 1. Trigger: "When record is created or updated" → "{{TABLE_NAME}}" table
 * 2. Action: "Run a script" → Paste this script
 * 3. Add input variable: recordId → Record ID from Step 1
 * 4. Test and enable
 */

// ══════════════════════════════════════════════════════════════
// CONFIGURATION
// ══════════════════════════════════════════════════════════════
const TABLE_NAME = "{{TABLE_NAME}}";

// ══════════════════════════════════════════════════════════════
// GET INPUT VARIABLE
// ══════════════════════════════════════════════════════════════
const inputConfig = input.config();
const recordId = inputConfig.recordId;

if (!recordId) {
    console.error("Missing input variable 'recordId'");
    console.error("Fix: In the 'Run a script' action, click '+ Add input variable(s)'");
    console.error("  Name: recordId");
    console.error("  Value: Select 'Record ID' from Step 1 (trigger)");
    throw new Error("recordId not configured");
}

// ══════════════════════════════════════════════════════════════
// FETCH WEBHOOK CONFIG FROM AIRTABLE
// ══════════════════════════════════════════════════════════════
const configTable = base.getTable("Invalidate Config");
const configRecords = await configTable.selectRecordsAsync();

const config = {};
for (const record of configRecords.records) {
    const key = record.getCellValue("key");
    const value = record.getCellValue("value");
    if (key && value) {
        config[key] = value;
    }
}

const WEBHOOK_URL = config.webhook_url;
const WEBHOOK_SECRET = config.webhook_secret;

if (!WEBHOOK_URL || !WEBHOOK_SECRET) {
    console.error("Missing webhook_url or webhook_secret in 'Invalidate Config' table");
    console.error("Fix: Create 'Invalidate Config' table with:");
    console.error("  Record 1: key='webhook_url', value='https://your-backend.com/api/webhooks/airtable'");
    console.error("  Record 2: key='webhook_secret', value='<your-generated-secret>'");
    throw new Error("Configuration missing");
}

// ══════════════════════════════════════════════════════════════
// FETCH THE RECORD
// ══════════════════════════════════════════════════════════════
const table = base.getTable(TABLE_NAME);
const record = await table.selectRecordAsync(recordId);

if (!record) {
    console.error(`Record ${recordId} not found in ${TABLE_NAME}`);
    throw new Error("Record not found");
}

// Extract all field values
// Use the table's field definitions to iterate over all fields
const tableFields = table.fields;
const fields = {};

for (const field of tableFields) {
    const fieldName = field.name;
    let value = record.getCellValue(fieldName);
    
    // Skip null/undefined values
    if (value === null || value === undefined) {
        continue;
    }
    
    // Transform linked records from [{id: 'recXXX', name: '...'}] to ['recXXX']
    // Airtable returns linked records as arrays of objects, but our backend expects arrays of IDs
    if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'object' && value[0] !== null && 'id' in value[0]) {
        value = value.map(item => item && item.id).filter(id => id);  // Filter out null/undefined
    }
    
    fields[fieldName] = value;
}

// Add record ID to fields
fields.id = record.id;

// ══════════════════════════════════════════════════════════════
// SEND WEBHOOK TO BACKEND
// ══════════════════════════════════════════════════════════════
const payload = {
    table: TABLE_NAME,
    record: fields,
    timestamp: new Date().toISOString(),
    record_id: record.id
};

try {
    const response = await fetch(WEBHOOK_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Airtable-Secret': WEBHOOK_SECRET
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        const errorText = await response.text();
        console.error(`Webhook failed: ${response.status} - ${errorText}`);
        throw new Error(`Webhook failed with status ${response.status}`);
    }

    const result = await response.json();
    console.log(`✓ Successfully sent ${TABLE_NAME} record ${record.id} to cache`);
    console.log(`  Response:`, result);
} catch (error) {
    console.error(`✗ Error sending webhook for ${TABLE_NAME}:`, error);
    throw error;
}
