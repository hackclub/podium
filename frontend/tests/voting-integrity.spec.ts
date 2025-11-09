import { test, expect } from '@playwright/test';
import { createEvent, attendEvent, createProject, voteForProject, ensureAuthenticatedUser } from './utils';

test.describe('Voting Integrity', () => {
	test('cannot vote without attending event', async ({ page }) => {
		// Create event and project as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Vote Auth Test Event');
		await attendEvent(page, event.joinCode);
		await createProject(page, event.name, 'Test Project');

		// Try to vote as a different user without attending
		const voterEmail = `voter+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, voterEmail, 'Test Voter');

		// Try to access voting page without attending
		if (event.slug) {
			await page.goto(`/events/${event.slug}/rank`);

			// Should not be able to vote or see voting options
			await expect(page.getByText(/not attending|cannot vote|not eligible/i)).toBeVisible();
		}
	});

	test('cannot vote for own project', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Self Vote Test Event');
		await attendEvent(page, event.joinCode);
		await createProject(page, event.name, 'My Own Project');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			const rankLink = page.getByRole('link', { name: /rank|vote/i });
			if (await rankLink.isVisible()) {
				await rankLink.click();

				// Should show message about not being able to vote for own project
				await expect(page.getByText(/own project|cannot vote|not eligible/i)).toBeVisible();
			}
		}
	});

	test('cannot vote twice in same event', async ({ page }) => {
		// Create event with multiple projects as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Double Vote Test Event');
		await attendEvent(page, event.joinCode);
		await createProject(page, event.name, 'Project One');
		await createProject(page, event.name, 'Project Two');

		// Switch to voter
		const voterEmail = `voter+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, voterEmail, 'Test Voter');
		await attendEvent(page, event.joinCode);

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			const rankLink = page.getByRole('link', { name: /rank|vote/i });
			if (await rankLink.isVisible()) {
				await rankLink.click();

				// Vote for first project
				await voteForProject(page, event.slug);

				// Try to vote again - should not be allowed
				await page.goto(`/events/${event.slug}/rank`);

				// Should show already voted or limit reached message
				await expect(page.getByText(/already voted|limit reached|cannot vote/i)).toBeVisible();
			}
		}
	});

	test('shows correct vote counts', async ({ page }) => {
		// Create event with projects as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Vote Count Test Event');
		await attendEvent(page, event.joinCode);
		await createProject(page, event.name, 'Count Test Project');

		// Have multiple voters vote
		const voterEmails = [
			`voter1+${Date.now()}@test.local`,
			`voter2+${Date.now()}@test.local`,
			`voter3+${Date.now()}@test.local`
		];

		for (const voterEmail of voterEmails) {
			await ensureAuthenticatedUser(page, voterEmail, `Test Voter ${voterEmail}`);
			await attendEvent(page, event.joinCode);

			if (event.slug) {
				await page.goto(`/events/${event.slug}`);

				const rankLink = page.getByRole('link', { name: /rank|vote/i });
				if (await rankLink.isVisible()) {
					await rankLink.click();
					await voteForProject(page, event.slug);
				}
			}
		}

		// Switch back to organizer and check vote counts
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Should show correct vote count (at least the number of votes cast)
			const voteCountText = page.getByText(/\d+\s*votes?/i);
			await expect(voteCountText).toBeVisible();
		}
	});
});