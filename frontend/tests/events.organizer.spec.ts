import { test, expect } from '@playwright/test';
import { createEvent, goToEventPage, ensureAuthenticatedUser } from './utils';

test.describe('Event Management - Organizer', () => {
	test('should create a new event', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Test Event', 'Test event for Playwright');

		// Event should be visible in events list
		await page.goto('/events');
		await expect(page.getByText('Events You Own')).toBeVisible();
		await expect(page.getByText(event.name)).toBeVisible();
	});

	test('should display event join code for owned event', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Join Code Test', 'Test event');

		// Verify join code is visible
		await expect(page.getByText(event.joinCode)).toBeVisible();
	});

	test('should navigate to event detail page', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Detail Test', 'Test event');

		// Navigate to event detail page
		if (event.slug) {
			await goToEventPage(page, event.slug);
			await expect(page).toHaveURL(new RegExp(`/events/${event.slug}`));
		}
	});

	test('should list events owned by user', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		// Create multiple events
		const event1 = await createEvent(page, 'Event One', 'First test event');
		const event2 = await createEvent(page, 'Event Two', 'Second test event');

		// Navigate to events page
		await page.goto('/events');

		// Both events should be visible
		await expect(page.getByText(event1.name)).toBeVisible();
		await expect(page.getByText(event2.name)).toBeVisible();
		await expect(page.getByText('Events You Own')).toBeVisible();
	});
});
