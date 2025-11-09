import { test, expect } from '@playwright/test';
import { createEvent, attendEvent, createProject, voteForProject, ensureAuthenticatedUser } from './utils';

test.describe('Voting and Leaderboard', () => {
	test('should allow voting on projects', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Voting Test Event', 'Test event for voting');
		await attendEvent(page, event.joinCode);

		// Create projects
		await createProject(page, event.name, 'Project One', 'First project');
		await createProject(page, event.name, 'Project Two', 'Second project');

		// Switch to voter user
		const voterEmail = `voter+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, voterEmail, 'Test Voter');

		// Join the event
		await attendEvent(page, event.joinCode);

		// Navigate to voting page
		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Look for rank/vote link
			const rankLink = page.getByRole('link', { name: /rank|vote/i });
			if (await rankLink.isVisible()) {
				await rankLink.click();

				// Should be on voting page
				await expect(page).toHaveURL(/\/rank/);

				// Vote for a project
				await voteForProject(page, event.slug);

				// Should see success feedback
				await expect(page.getByText(/voted|submitted|thanks/i)).toBeVisible();
			}
		}
	});

	test('should display leaderboard page', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Leaderboard Test Event', 'Leaderboard test');

		// Navigate to event page
		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			// Check for leaderboard link
			const leaderboardLink = page.getByRole('link', { name: /leaderboard/i });
			if (await leaderboardLink.isVisible()) {
				await leaderboardLink.click();

				// Should be on leaderboard page
				await expect(page).toHaveURL(/\/leaderboard/);

				// Should see leaderboard heading or content
				await expect(page.getByRole('heading', { name: /leaderboard|results/i })).toBeVisible();
			}
		}
	});

	test('should prevent voting for own project', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Own Project Vote Test', 'Test voting for own project');
		await attendEvent(page, event.joinCode);

		// Create a project
		const project = await createProject(page, event.name, 'My Own Project', 'My project');

		// Navigate to voting page
		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			const rankLink = page.getByRole('link', { name: /rank|vote/i });
			if (await rankLink.isVisible()) {
				await rankLink.click();

				// Should not be able to vote for own project (or should see appropriate message)
				await expect(page.getByText(/own project|cannot vote|not eligible/i)).toBeVisible();
			}
		}
	});

	test('should show voting progress and limits', async ({ page }) => {
		// Create event with multiple projects as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Voting Limits Test', 'Test voting limits');
		await attendEvent(page, event.joinCode);

		// Create multiple projects
		for (let i = 1; i <= 5; i++) {
			await createProject(page, event.name, `Project ${i}`, `Project ${i} description`);
		}

		// Switch to voter
		const voterEmail = `voter+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, voterEmail, 'Test Voter');
		await attendEvent(page, event.joinCode);

		// Navigate to voting page
		if (event.slug) {
			await page.goto(`/events/${event.slug}`);

			const rankLink = page.getByRole('link', { name: /rank|vote/i });
			if (await rankLink.isVisible()) {
				await rankLink.click();

				// Should show voting instructions/limits
				await expect(page.getByText(/vote|remaining|can vote/i)).toBeVisible();
			}
		}
	});
});
