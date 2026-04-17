import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { createTestEvent, attendEvent, adminPatchEvent } from './helpers/api';
import { createUserAndGetToken, secondaryUserEmail } from './helpers/users';

test.describe('Permissions', () => {
	/**
	 * The event owner sees the Admin Panel section on the event page.
	 * The panel only renders when the server confirms ownership via EventPrivate.
	 */
	test('event owner sees admin panel on event page', async ({ authedPage, authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Owner Admin', testInfo) });
		await attendEvent(authedApi, event.id);

		const attendeesLoaded = authedPage.waitForResponse(
			(r) => r.url().includes('/attendees') && r.ok(),
			{ timeout: 15000 }
		);
		await authedPage.goto(`/events/${event.slug}`);
		await attendeesLoaded;

		await expect(authedPage.getByText('Admin Panel')).toBeVisible({ timeout: 5000 });
		await expect(authedPage.getByRole('heading', { name: /event attendees/i })).toBeVisible({ timeout: 5000 });
	});

	/**
	 * A user who did not create the event never sees the Admin Panel,
	 * even when attending as a regular participant.
	 */
	test('non-owner attendee does not see admin panel', async ({ authedPage, authedApi }, testInfo) => {
		const tag = `${Date.now()}-w${testInfo.workerIndex}`;

		const ownerEmail = secondaryUserEmail('organizer', tag);
		const { authedApi: ownerApi, api: ownerBase } = await createUserAndGetToken(ownerEmail, 'Event Owner');
		let event: { id: string; slug: string };
		try {
			const resp = await ownerApi.post('/events/test/create', {
				data: { name: unique('Non-Owner Perm', testInfo) },
			});
			event = await resp.json();
		} finally {
			await ownerApi.dispose();
			await ownerBase.dispose();
		}

		await attendEvent(authedApi, event.id);

		const adminAttempt = authedPage.waitForResponse(
			(r) => r.url().includes(`/events/admin/${event.id}`) && r.request().method() === 'GET',
			{ timeout: 15000 }
		);
		await authedPage.goto(`/events/${event.slug}`);
		await adminAttempt;

		await expect(authedPage.getByText('Admin Panel')).not.toBeVisible({ timeout: 3000 });
	});

	/**
	 * The public leaderboard page is accessible to any attendee of the event.
	 * The leaderboard endpoint requires CLOSED phase, so we patch it first.
	 */
	test('attendee can access the public leaderboard page', async ({ authedPage, authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Leaderboard Access', testInfo) });
		await attendEvent(authedApi, event.id);
		// Leaderboard is only served in CLOSED phase
		await adminPatchEvent(authedApi, event.id, { phase: 'closed' });

		// Load function runs server-side (SSR) so waitForResponse won't catch it
		await authedPage.goto(`/events/${event.slug}/leaderboard`);
		await expect(authedPage.getByRole('heading', { name: 'Leaderboard', exact: true })).toBeVisible({ timeout: 10000 });
	});

	/**
	 * An unauthenticated user is redirected away from the home page
	 * and does not see authenticated content.
	 */
	test('unauthenticated user does not see wizard or project actions', async ({ page }) => {
		await page.goto('/');
		// Should not see the wizard's primary CTA
		await expect(page.getByRole('button', { name: /create.*project/i })).not.toBeVisible({ timeout: 5000 });
	});
});
