import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { createTestEvent, attendEvent } from './helpers/api';

test.describe('Project Submission Wizard', () => {
	test('should show project submission wizard after event selection', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Wizard Event', testInfo);

		// Create test event and attend via API
		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		// Navigate to home and wait for the full onMount data-load to finish.
		// The heading renders immediately, but the wizard buttons only appear after
		// /events/official → /events/ → /projects/mine all resolve.
		const projectsMineResponse = authedPage.waitForResponse(
			(res) => res.url().includes('/projects/mine') && res.request().method() === 'GET',
			{ timeout: 20000 }
		);
		await authedPage.reload();
		await projectsMineResponse;

		// Should see project submission wizard with welcome message and action buttons
		await expect(authedPage.getByRole('heading', { name: /welcome/i }).first()).toBeVisible({ timeout: 15000 });
		await expect(authedPage.getByRole('button', { name: /create.*project/i })).toBeVisible({ timeout: 15000 });
		await expect(authedPage.getByRole('button', { name: /join.*project/i })).toBeVisible({ timeout: 15000 });
	});

	test('should navigate to create project form', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Create Wizard', testInfo);

		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		const projectsMineResponse = authedPage.waitForResponse(
			(res) => res.url().includes('/projects/mine') && res.request().method() === 'GET',
			{ timeout: 20000 }
		);
		await authedPage.reload();
		await projectsMineResponse;

		await authedPage.getByRole('button', { name: /create.*project/i }).click();

		await expect(authedPage.locator('#project_name, input[name="name"]').first()).toBeVisible({ timeout: 10000 });
	});

	test('should navigate to join project form', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Join Wizard', testInfo);

		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		const projectsMineResponse = authedPage.waitForResponse(
			(res) => res.url().includes('/projects/mine') && res.request().method() === 'GET',
			{ timeout: 20000 }
		);
		await authedPage.reload();
		await projectsMineResponse;

		await authedPage.getByRole('button', { name: /join.*project/i }).click();

		await expect(
			authedPage.locator('input[placeholder*="code" i], #join_code').first()
		).toBeVisible({ timeout: 10000 });
	});
});
