/**
 * Superadmin CSV export tests.
 *
 * These are API-level tests — no browser needed. They verify the data mapping
 * from the DB to CSV rows, not the superadmin UI itself.
 */

import { test, expect } from './fixtures/superadmin';
import { createTestEvent, attendEvent, createProject, superadminExportCsv } from './helpers/api';
import { unique } from './utils/data';

// Column names must match _CSV_COLUMNS in superadmin.py exactly.
const EXPECTED_COLUMNS = [
	'First Name', 'Last Name', 'Email',
	'Playable URL', 'Code URL', 'Screenshot', 'Description',
	'GitHub Username',
	'Address (Line 1)', 'Address (Line 2)', 'City', 'State / Province',
	'Country', 'ZIP / Postal Code', 'Birthday',
	'Override Hours Spent',
];

/**
 * Parse a CSV string into an array of row objects keyed by header.
 * Handles Python csv.DictWriter output — no embedded newlines or commas in test data.
 */
function parseCSV(text: string): Record<string, string>[] {
	const lines = text.trim().split('\n');
	const headers = lines[0].split(',');
	return lines.slice(1).map((line) => {
		const values = line.split(',');
		return Object.fromEntries(headers.map((h, i) => [h.trim(), (values[i] ?? '').trim()]));
	});
}

test.describe('Superadmin CSV Export', () => {
	test('non-superadmin user gets 403', async ({ authedApi }) => {
		const resp = await authedApi.get('/superadmin/export-csv?series=test');
		expect(resp.status()).toBe(403);
	});

	test('400 when neither event_id nor series is provided', async ({ superadminApi }) => {
		const resp = await superadminApi.get('/superadmin/export-csv');
		expect(resp.status()).toBe(400);
	});

	test('export by event_id: correct columns, row count, and field values', async (
		{ authedApi, superadminApi, userEmail },
		testInfo
	) => {
		const event = await createTestEvent(authedApi, { name: unique('CSV Export', testInfo) });
		await attendEvent(authedApi, event.id);
		await createProject(authedApi, {
			name: unique('Export Project', testInfo),
			description: 'A test project',
			event_id: event.id,
			// GitHub username should be extracted as 'hackclub'
			repo: 'https://github.com/hackclub/sprig',
			image_url: 'https://example.com/image.png',
			demo: 'https://example.com/demo',
			hours_spent: 5,
		});

		const resp = await superadminExportCsv(superadminApi, { event_id: event.id });
		expect(resp.ok()).toBeTruthy();
		expect(resp.headers()['content-type']).toContain('text/csv');

		const rows = parseCSV(await resp.text());

		// Exactly one project in this event
		expect(rows).toHaveLength(1);

		const row = rows[0];

		// All expected columns are present
		for (const col of EXPECTED_COLUMNS) {
			expect(row).toHaveProperty(col);
		}

		// Field mapping correctness
		expect(row['Email']).toBe(userEmail);
		expect(row['GitHub Username']).toBe('hackclub');
		expect(row['Code URL']).toBe('https://github.com/hackclub/sprig');
		expect(row['Playable URL']).toBe('https://example.com/demo');
		expect(row['Birthday']).toBe('2000-01-01'); // matches fixture user's dob
		expect(row['Address (Line 1)']).toBe('123 Test St');
		expect(row['City']).toBe('Testville');
		expect(row['Country']).toBe('US');
		expect(row['Override Hours Spent']).toBe('5');
	});

	test('export by series spans all events with that flag', async (
		{ authedApi, superadminApi },
		testInfo
	) => {
		// Test events are created with feature_flags_csv = active_event_series
		const event1 = await createTestEvent(authedApi, { name: unique('Series Export A', testInfo) });
		const event2 = await createTestEvent(authedApi, { name: unique('Series Export B', testInfo) });
		const series = event1.feature_flags_csv as string;

		await attendEvent(authedApi, event1.id);
		await createProject(authedApi, {
			name: unique('Project A', testInfo),
			description: 'Project in event 1',
			event_id: event1.id,
			repo: 'https://github.com/hackclub/project-a',
			image_url: 'https://example.com/a.png',
		});

		await attendEvent(authedApi, event2.id);
		await createProject(authedApi, {
			name: unique('Project B', testInfo),
			description: 'Project in event 2',
			event_id: event2.id,
			repo: 'https://github.com/hackclub/project-b',
			image_url: 'https://example.com/b.png',
		});

		const resp = await superadminExportCsv(superadminApi, { series });
		expect(resp.ok()).toBeTruthy();

		const rows = parseCSV(await resp.text());
		// Both events contribute one row each (at minimum — other worker tests may add more)
		expect(rows.length).toBeGreaterThanOrEqual(2);
	});

	test('series export returns 404 when no events match', async ({ superadminApi }) => {
		const resp = await superadminExportCsv(superadminApi, { series: 'nonexistent-series-xyz-99' });
		expect(resp.status()).toBe(404);
	});
});
