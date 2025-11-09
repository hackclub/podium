import { test, expect } from '@playwright/test';
import { createEvent, attendEvent, ensureAuthenticatedUser } from './utils';

test.describe('Event Management - Attendee', () => {
	test('should join an event with join code', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'Join Test Event', 'Test event for joining');

		// Switch to attendee user
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');

		// Join the event
		await attendEvent(page, event.joinCode, 'Playwright test');

		// Navigate to events page and verify event appears in attending list
		await page.goto('/events');

		// Should see the event in the "Events You're Attending" section
		await expect(page.getByRole('heading', { name: "Events You're Attending" })).toBeVisible();

		// Find event link (attending events don't show join codes)
		await expect(page.getByRole('link', { name: event.name, exact: true })).toBeVisible();
	});

	test('should see event details after joining', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'Detail View Event', 'Test event for viewing details');

		// Switch to attendee user
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');

		// Join the event
		await attendEvent(page, event.joinCode);

		// Navigate to event detail page
		if (event.slug) {
			await page.goto(`/events/${event.slug}`);
			await expect(page.getByRole('heading', { name: event.name })).toBeVisible();
		}
	});

	test('should handle invalid join code', async ({ page }) => {
		const email = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Attendee');

		await page.goto('/events/attend');
		await page.locator('#join_code').fill('INVALID123');

		await page.getByRole('button', { name: /join.*event/i }).click();

		// Should show error message
		await expect(page.getByText(/invalid|not found|error/i)).toBeVisible();
	});

	test('should handle duplicate event join', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'Duplicate Join Event', 'Test event for duplicate joining');

		// Switch to attendee user
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');

		// Join the event first time
		await attendEvent(page, event.joinCode);

		// Try to join again
		await page.goto('/events/attend');
		await page.locator('#join_code').fill(event.joinCode);
		await page.getByRole('button', { name: /join.*event/i }).click();

		// Should handle gracefully (idempotent)
		await expect(page.getByText(/joined|already|success/i)).toBeVisible();
	});

	test('should handle join link with pre-filled join code', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'Join Link Event', 'Test event for join links');

		// Switch to attendee user
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');

		// Navigate to attend page with join code in URL
		await page.goto(`/events/attend?join_code=${event.joinCode}`);

		// Join code should be pre-filled
		await expect(page.locator('#join_code')).toHaveValue(event.joinCode);

		// Fill referral and submit
		await page.locator('#referral').fill('From join link test');
		await page.getByRole('button', { name: /join.*event/i }).click();

		// Should join successfully
		await expect(page.getByText(/joined.*successfully|success/i)).toBeVisible();
	});

	test('should create new account when joining via link', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'New Account Join Event', 'Test event for new account join');

		// Clear auth to simulate new user
		await page.evaluate(() => localStorage.clear());
		await page.context().clearCookies();

		// Navigate to join link (this should redirect to login since not authenticated)
		await page.goto(`/events/attend?join_code=${event.joinCode}`);

		// Should redirect to login or show login form
		await page.waitForURL(/\/login/);

		// Create new account
		const newUserEmail = `newuser+${Date.now()}@test.local`;
		await page.locator('#email').fill(newUserEmail);
		await page.getByRole('button', { name: /login|sign up/i }).click();

		// Should see signup form
		await expect(page.locator('#first_name')).toBeVisible();

		// Fill signup form
		await page.locator('#first_name').fill('New');
		await page.locator('#last_name').fill('User');
		await page.locator('#display_name').fill('New Test User');
		await page.locator('#phone').fill('5551234567');
		await page.locator('#street_1').fill('123 Test St');
		await page.locator('#city').fill('Testville');
		await page.locator('#state').fill('CA');
		await page.locator('#zip_code').fill('12345');
		await page.locator('#country').selectOption('US');
		await page.locator('#dob').fill('2000-01-01');

		await page.getByRole('button', { name: /login|sign up/i }).click();

		// Should complete signup
		await expect(page.getByText(/account created|signed up|success/i)).toBeVisible();
	});
});
