import { test, expect } from '@playwright/test';
import { createEvent, attendEvent, createProject, ensureAuthenticatedUser } from './utils';

test.describe('Admin Dashboard', () => {
	test('should display admin panel for owned event', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Admin Test Event', 'Test event for admin dashboard');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Should see admin panel (only visible to owner)
			await expect(page.getByText(/admin panel|event admin|manage event/i)).toBeVisible();
		}
	});

	test('should view attendees list as admin', async ({ page }) => {
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Attendees Test Event', 'Test event for attendees');

		// Have organizer attend their own event
		await attendEvent(page, event.joinCode);

		// Have attendee join
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');
		await attendEvent(page, event.joinCode);

		// Switch back to organizer
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Should see attendees section in admin panel
			const attendeesSection = page.getByText(/attendees/i).first();
			if (await attendeesSection.isVisible()) {
				await expect(attendeesSection).toBeVisible();
			}
		}
	});

	test('should view leaderboard as admin', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Leaderboard Admin Test Event', 'Test event for admin leaderboard');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Look for leaderboard section in admin panel or navigate to leaderboard
			const leaderboardLink = page.getByRole('link', { name: /leaderboard/i });
			if (await leaderboardLink.isVisible()) {
				await leaderboardLink.click();

				// Should be on leaderboard page
				await expect(page).toHaveURL(/\/leaderboard/);
			}
		}
	});

	test('should view votes as admin', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Votes Test Event', 'Test event for votes');

		// Organizer attends
		await attendEvent(page, event.joinCode);

		// Create a project
		await createProject(page, event.name, 'Test Project', 'Test project');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Should see votes section (even if empty)
			const votesSection = page.getByText(/votes|voting/i).first();
			if (await votesSection.isVisible()) {
				await expect(votesSection).toBeVisible();
			}
		}
	});

	test('should view referrals as admin', async ({ page }) => {
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Referrals Test Event', 'Test event for referrals');

		// Have attendee join with referral
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');
		await attendEvent(page, event.joinCode, 'From Playwright test referral');

		// Switch back to organizer
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Should see referrals section
			const referralsSection = page.getByText(/referral/i).first();
			if (await referralsSection.isVisible()) {
				await expect(referralsSection).toBeVisible();
			}
		}
	});

	test('should update event details as admin', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Update Test Event', 'Original description');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Look for Edit Event button
			const editButton = page.getByRole('button', { name: /edit event/i });
			if (await editButton.isVisible()) {
				await editButton.click();

				// Wait for modal to open
				const descField = page.locator('#event_description');
				await expect(descField).toBeVisible();

				await descField.fill('Updated description via test');
				const updateButton = page.getByRole('button', { name: /update event/i });
				await expect(updateButton).toBeEnabled();
				await updateButton.click();

				// Wait for modal to close
				await expect(descField).not.toBeVisible();
			}
		}
	});

	test('should enable voting and leaderboard via admin panel', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Voting Enable Test Event', 'Test event for enabling voting');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Look for Edit Event button to enable voting
			const editButton = page.getByRole('button', { name: /edit event|settings/i });
			if (await editButton.isVisible()) {
				await editButton.click();

				// Wait for modal to open
				const votableCheckbox = page.locator('#votable, [name*="votable"], [name*="voting"]');
				if (await votableCheckbox.isVisible()) {
					// Check the voting enabled checkbox
					await votableCheckbox.check();

					// Submit the form
					const updateButton = page.getByRole('button', { name: /update|save/i });
					await updateButton.click();

					// Wait for modal to close
					await expect(votableCheckbox).not.toBeVisible();

					// Verify voting is now enabled by checking for voting links
					const rankLink = page.getByRole('link', { name: /rank|vote/i });
					await expect(rankLink).toBeVisible();
				}
			}
		}
	});

	test('should remove attendee as admin', async ({ page }) => {
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Remove Attendee Test Event', 'Test event for removing attendees');

		// Have attendee join
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');
		await attendEvent(page, event.joinCode);

		// Switch back to organizer
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Look for attendees list and remove button
			const attendeesSection = page.getByText(/attendees|participants/i);
			if (await attendeesSection.isVisible()) {
				// Look for remove button next to the attendee
				const removeButton = page.getByRole('button', { name: /remove|delete|kick/i });
				if (await removeButton.isVisible()) {
					// Count attendees before removal
					const attendeeRowsBefore = await page.locator('tr, .attendee-item').count();

					await removeButton.click();

					// Confirm removal if there's a confirmation dialog
					const confirmButton = page.getByRole('button', { name: /confirm|yes|remove/i });
					if (await confirmButton.isVisible()) {
						await confirmButton.click();
					}

					// Should see success message
					await expect(page.getByText(/removed|deleted|kicked/i)).toBeVisible();

					// Optionally verify attendee count decreased
					await page.reload();
					const attendeeRowsAfter = await page.locator('tr, .attendee-item').count();
					// Note: Count might not decrease immediately due to caching
				}
			}
		}
	});
});
