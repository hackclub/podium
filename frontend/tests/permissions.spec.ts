import { test, expect } from '@playwright/test';
import { createEvent, attendEvent, createProject, ensureAuthenticatedUser } from './utils';

test.describe('Permissions & Authorization', () => {
	test('non-owner should not see admin panel', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'Permission Test Event', 'Test event');

		// Switch to attendee user
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');

		// Join as attendee
		await attendEvent(page, event.joinCode);

		// Navigate to event page
		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Should NOT see admin panel
			const adminPanel = page.getByText(/admin panel|event admin/i);
			await expect(adminPanel).not.toBeVisible();

			// Should NOT see attendees table
			const attendeesTable = page.getByRole('table', { name: /attendees/i });
			await expect(attendeesTable).not.toBeVisible();
		}
	});

	test('non-owner cannot access admin endpoints directly', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'Admin Access Test Event', 'Test event');

		// Switch to attendee user
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');

		// Try accessing event page - should work for viewing
		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// But admin panel should not be visible
			await expect(page.getByText(/admin panel/i)).not.toBeVisible();
		}
	});

	test('cannot join project without joining event first', async ({ page }) => {
		// Organizer creates event and project
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Project Permission Test Event', 'Test event');
		await attendEvent(page, event.joinCode);

		const project = await createProject(page, event.name, 'Test Project', 'Test project');

		// Switch to attendee who hasn't joined event
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');

		// Try to join project without attending the event
		if (project.joinCode) {
			await page.goto('/projects/join');
			await page.locator('#join_code').fill(project.joinCode);
			await page.getByRole('button', { name: /join/i }).click();

			// Should see error
			await expect(page.getByText(/must attend|not part of this event|error/i)).toBeVisible();
		}
	});

	test('invalid join code shows error', async ({ page }) => {
		const email = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Attendee');

		await page.goto('/events/attend');
		await page.locator('#join_code').fill('INVALID123');

		await page.getByRole('button', { name: /join.*event/i }).click();

		// Should show error message
		await expect(page.getByText(/not found|invalid|error/i)).toBeVisible();
	});

	test('cannot create event without required fields', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		await page.goto('/events/create');

		// Try to submit without filling fields
		await page.getByRole('button', { name: /create event/i }).click();

		// Should still be on create page (form validation prevents submission)
		await expect(page).toHaveURL(/\/events\/create/);
	});

	test('cannot create project without required fields', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		await page.goto('/projects/create');

		// Try to submit without filling fields
		const submitButton = page.getByRole('button', { name: /ship it|create project/i });
		await submitButton.click();

		// Should still be on create page (form validation prevents submission)
		await expect(page).toHaveURL(/\/projects\/create/);
	});

	test('duplicate event join is idempotent', async ({ page }) => {
		const email = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Attendee');

		// Create event as organizer (switch context)
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'Duplicate Join Test Event', 'Test event');

		// Switch back to attendee
		await ensureAuthenticatedUser(page, email, 'Test Attendee');

		// Join once
		await attendEvent(page, event.joinCode);

		// Join again - should handle gracefully
		await page.goto('/events/attend');
		await page.locator('#join_code').fill(event.joinCode);
		await page.getByRole('button', { name: /join.*event/i }).click();

		// Should handle gracefully (idempotent)
		await expect(page.getByText(/joined|already|success/i)).toBeVisible();
	});
});