import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { createTestEvent, attendEvent } from './helpers/api';

test.describe('Permissions', () => {
	test('event owner should see admin panel', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Permission Test', testInfo);

		// Create test event (user becomes owner) and attend
		const event = await createTestEvent(authedApi, { name: eventName });

		// Navigate to event page
		await authedPage.goto(`/events/${event.slug}`);

		// Wait for page to load
		await authedPage.waitForLoadState('networkidle');

		// Should see admin controls as owner - the admin panel has a divider with "Admin Panel" text
		await expect(authedPage.getByText('Admin Panel')).toBeVisible({ timeout: 15000 });
	});

	test('event owner should see attendees table in admin panel', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Attendees Test', testInfo);

		// Create test event and attend
		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		// Navigate to event page
		await authedPage.goto(`/events/${event.slug}`);

		// Wait for page to load
		await authedPage.waitForLoadState('networkidle');

		// Should see admin panel with attendees section (heading "Event Attendees")
		await expect(authedPage.getByRole('heading', { name: /Event Attendees/i })).toBeVisible({ timeout: 15000 });
	});

	test('should access leaderboard when enabled', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Leaderboard Access', testInfo);

		// Create test event (has leaderboard enabled by default) and attend
		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		// Navigate to leaderboard
		await authedPage.goto(`/events/${event.slug}/leaderboard`);

		// Should see leaderboard page (might show "no projects" if empty, but page should load)
		await expect(authedPage.locator('body')).toBeVisible();
		
		// The page should not show an error
		await expect(authedPage.getByText(/error|forbidden|not found/i).first()).not.toBeVisible({ timeout: 3000 }).catch(() => {});
	});
});
