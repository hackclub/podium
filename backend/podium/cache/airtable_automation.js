/**
 * Airtable Automation Script
 * 
 * Setup: Create separate automations for each table (Users, Events, Projects, Votes, Referrals)
 * Trigger: "When record created or updated"
 * Action: "Run script"
 * 
 * Configuration:
 * 1. Create an "Invalidate Config" table with fields: "key" (text), "value" (text)
 * 2. Add two records:
 *    - key: "webhook_url", value: "https://your-backend.com/api/webhooks/airtable"
 *    - key: "webhook_secret", value: "your-secret-key-here"
 * 3. Select the appropriate TABLE_NAME for each automation
 */

// ===== CONFIGURATION =====
const TABLE_NAME = "Projects"; // Change per automation: "Users", "Events", "Projects", "Votes", "Referrals"

// Fetch config from Airtable
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
    console.error("Missing webhook_url or webhook_secret in Invalidate Config table");
    throw new Error("Configuration missing");
}

// ===== SCRIPT =====
const inputConfig = input.config();
const recordId = inputConfig.recordId;

// Fetch the full record that triggered the automation
const table = base.getTable(TABLE_NAME);
const queryResult = await table.selectRecordsAsync();
const record = queryResult.records.find(r => r.id === recordId);

if (!record) {
    console.error(`Record ${recordId} not found in ${TABLE_NAME}`);
    throw new Error("Record not found");
}

// Extract all field values
const fields = {};
for (const [fieldName, value] of Object.entries(record._rawJson.fields)) {
    fields[fieldName] = value;
}

// Add record ID to fields
fields.id = record.id;

// Prepare webhook payload
const payload = {
    table: TABLE_NAME,
    record: fields,
    timestamp: new Date().toISOString(),
    // Include record ID separately for easier processing
    record_id: record.id
};

// Send to backend
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
    console.log(`Successfully sent ${TABLE_NAME} record ${recordId} to backend:`, result);
} catch (error) {
    console.error(`Error sending webhook for ${TABLE_NAME}:`, error);
    throw error;
}

/**
 * SETUP INSTRUCTIONS:
 * 
 * For each table (Users, Events, Projects, Votes, Referrals):
 * 
 * 1. Create a new Automation in Airtable
 * 2. Name it: "Sync [TableName] to Cache"
 * 3. Trigger: "When record is created or updated"
 *    - Select the specific table
 *    - (Optional) Add conditions if you want to filter which records trigger
 * 4. Action: "Run script"
 *    - Paste this code
 *    - Update TABLE_NAME constant to match (e.g., "Projects", "Users")
 *    - Set WEBHOOK_URL to your backend URL
 *    - Set WEBHOOK_SECRET to match your backend configuration
 * 5. Test the automation with a sample record update
 * 6. Enable the automation
 * 
 * NOTES:
 * - Airtable Enterprise has no automation limits
 * - The script sends the FULL record to your backend (all fields)
 * - Linked records are sent as arrays of record IDs (Airtable standard)
 * - Your backend will validate the secret and update the cache
 */
