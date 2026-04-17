import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { createTestEvent, attendEvent, createProject } from './helpers/api';
import { createUserAndGetToken, secondaryUserEmail } from './helpers/users';

test.describe('Admin Panel', () => {
	/**
	 * Event owner changes the event phase via the timeline select dropdown.
	 * Verifies the PATCH fires, succeeds, and the UI reflects the new phase.
	 */
	test('owner can change event phase via timeline', async ({ authedPage, authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Phase Change', testInfo) });
		await attendEvent(authedApi, event.id);

		// Register before navigation so we don't miss the response
		const attendeesLoaded = authedPage.waitForResponse(
			(r) => r.url().includes('/attendees') && r.ok(),
			{ timeout: 15000 }
		);
		await authedPage.goto(`/events/${event.slug}`);
		await attendeesLoaded;

		// The select is the unambiguous phase control (timeline steps are harder to target reliably)
		const phaseSelect = authedPage.getByRole('combobox');
		await expect(phaseSelect).toBeVisible({ timeout: 10000 });
		await expect(phaseSelect).toHaveValue('voting'); // test events start in voting phase

		const patchDone = authedPage.waitForResponse(
			(r) => r.url().includes(`/events/admin/${event.id}`) && r.request().method() === 'PATCH' && r.ok(),
			{ timeout: 10000 }
		);
		await phaseSelect.selectOption('closed');
		await patchDone;

		// Description text updates to reflect new phase
		await expect(authedPage.getByText(/voting closed.*leaderboard visible/i)).toBeVisible({ timeout: 5000 });
	});

	/**
	 * Event owner removes an attendee through the attendees table UI.
	 * Uses a second user (created via API) as the attendee being removed.
	 */
	test('owner can remove an attendee via the attendees table', async ({ authedPage, authedApi }, testInfo) => {
		const tag = `${Date.now()}-w${testInfo.workerIndex}`;
		const event = await createTestEvent(authedApi, { name: unique('Remove Attendee', testInfo) });
		await attendEvent(authedApi, event.id);

		// Second user attends
		const attendeeEmail = secondaryUserEmail('attendee', tag);
		const { authedApi: attendeeApi, api: attendeeBase } = await createUserAndGetToken(
			attendeeEmail,
			'Test Attendee'
		);
		try {
			await attendEvent(attendeeApi, event.id);
		} finally {
			await attendeeApi.dispose();
			await attendeeBase.dispose();
		}

		const attendeesLoaded = authedPage.waitForResponse(
			(r) => r.url().includes('/attendees') && r.ok(),
			{ timeout: 15000 }
		);
		await authedPage.goto(`/events/${event.slug}`);
		await attendeesLoaded;

		// Attendee row must be present before we try to remove
		const attendeeRow = authedPage.locator('tr').filter({ hasText: attendeeEmail });
		await expect(attendeeRow).toBeVisible({ timeout: 5000 });

		await attendeeRow.getByRole('button', { name: 'Remove' }).click();

		// Confirmation modal appears — click the modal's Remove button
		const modalRemove = authedPage.locator('.modal-box').getByRole('button', { name: 'Remove' });
		await expect(modalRemove).toBeVisible({ timeout: 5000 });

		const removeResp = authedPage.waitForResponse(
			(r) => r.url().includes('/remove-attendee') && r.request().method() === 'POST' && r.ok(),
			{ timeout: 10000 }
		);
		await modalRemove.click();
		await removeResp;

		// Row disappears after removal
		await expect(attendeeRow).not.toBeVisible({ timeout: 5000 });
	});

	/**
	 * Admin leaderboard shows projects with a validation status badge.
	 * Validation is non-blocking — badges appear regardless of status.
	 */
	test('admin leaderboard shows validation status badge per project', async ({ authedPage, authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Leaderboard Badge', testInfo) });
		await attendEvent(authedApi, event.id);

		await createProject(authedApi, {
			name: 'Badge Test Project',
			description: 'Validation badge test',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md',
			repo: 'https://github.com/hackclub/podium',
			event_id: event.id,
		});

		const leaderboardLoaded = authedPage.waitForResponse(
			(r) => r.url().includes('/leaderboard') && r.ok(),
			{ timeout: 15000 }
		);
		await authedPage.goto(`/events/${event.slug}`);
		await leaderboardLoaded;

		// Project appears in the admin leaderboard section
		const leaderboardSection = authedPage.locator('.card').filter({ hasText: 'Admin Leaderboard' });
		await expect(leaderboardSection.getByText('Badge Test Project')).toBeVisible({ timeout: 5000 });

		// Each project card has a validation status badge
		await expect(
			leaderboardSection.locator('.badge').filter({ hasText: /pending|valid|warning/i }).first()
		).toBeVisible({ timeout: 5000 });
	});

	/**
	 * A user who is not the event owner should not see the Admin Panel section,
	 * even if they are attending the event.
	 */
	test('non-owner attending the event does not see admin panel', async ({ authedPage, authedApi }, testInfo) => {
		const tag = `${Date.now()}-w${testInfo.workerIndex}`;

		// A different user creates the event
		const ownerEmail = secondaryUserEmail('organizer', tag);
		const { authedApi: ownerApi, api: ownerBase } = await createUserAndGetToken(ownerEmail, 'Event Owner');
		let event: { id: string; slug: string };
		try {
			const resp = await ownerApi.post('/events/test/create', {
				data: { name: unique('Non-Owner', testInfo) },
			});
			event = await resp.json();
		} finally {
			await ownerApi.dispose();
			await ownerBase.dispose();
		}

		// Fixture user attends but is not the owner
		await attendEvent(authedApi, event.id);

		// The layout always calls GET /events/admin/{id} for authenticated users
		// (returns 403 for non-owners). Wait for it before asserting absence.
		const adminAttempt = authedPage.waitForResponse(
			(r) => r.url().includes(`/events/admin/${event.id}`) && r.request().method() === 'GET',
			{ timeout: 15000 }
		);
		await authedPage.goto(`/events/${event.slug}`);
		await adminAttempt;

		await expect(authedPage.getByText('Admin Panel')).not.toBeVisible({ timeout: 3000 });
	});
});
