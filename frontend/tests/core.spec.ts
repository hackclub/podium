import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { createTestEvent, attendEvent } from './helpers/api';

test.describe('Core Functionality', () => {
	test('should create test event and show it in official events list', async ({ authedApi }, testInfo) => {
		const eventName = unique('Official Event', testInfo);

		// Create test event via API (admin/test endpoint)
		const event = await createTestEvent(authedApi, { name: eventName, description: 'Test event' });

		// Verify the event appears in official events list
		const response = await authedApi.get('/events/official');
		expect(response.ok()).toBe(true);
		const events = await response.json();
		expect(events.some((e: any) => e.name === eventName)).toBe(true);
	});

	test('should attend official event via API', async ({ authedApi }, testInfo) => {
		const eventName = unique('Attend Test', testInfo);

		// Create test event via API
		const event = await createTestEvent(authedApi, { name: eventName });

		// Attend the event
		const attendResp = await attendEvent(authedApi, event.id);
		expect(attendResp.message).toMatch(/joined|attending/i);
	});

	test('should show project submission wizard after attending', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Wizard Test', testInfo);

		// Create test event and attend via API
		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		// Force a full reload so onMount re-fires with the newly attended event.
		// Register the waitForResponse listener BEFORE reload to guarantee we don't miss it.
		const projectsMineResponse = authedPage.waitForResponse(
			(r) => r.url().includes('/projects/mine') && r.status() === 200,
			{ timeout: 20000 }
		);
		await authedPage.reload();
		await projectsMineResponse;

		// Should see project submission wizard with event name and create/join buttons
		await expect(
			authedPage.getByRole('button', { name: /create.*project/i }).first()
		).toBeVisible({ timeout: 10000 });
	});

	test('should see event details after attending', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Details Test', testInfo);

		// Create test event and attend via API
		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		// Navigate to event page
		await authedPage.goto(`/events/${event.slug}`);

		// Should see event name
		await expect(authedPage.getByText(eventName).first()).toBeVisible({ timeout: 10000 });
	});

	test('should see leaderboard link for attended event', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Leaderboard Test', testInfo);

		// Create test event and attend via API
		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		// Navigate to event page
		await authedPage.goto(`/events/${event.slug}`);

		// Should have leaderboard link
		await expect(authedPage.locator('a[href*="/leaderboard"]').first()).toBeVisible({ timeout: 10000 });
	});
});
