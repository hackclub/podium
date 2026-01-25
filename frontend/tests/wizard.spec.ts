import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { createTestEvent, attendEvent } from './helpers/api';

test.describe('Project Submission Wizard', () => {
	test('should show project submission wizard after event selection', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Wizard Event', testInfo);

		// Create test event and attend via API
		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		// Navigate to home
		await authedPage.goto('/');

		// Should see project submission wizard with welcome message
		await expect(authedPage.getByRole('heading', { name: /welcome/i }).first()).toBeVisible({ timeout: 10000 });

		// Should have create and join project buttons
		await expect(authedPage.getByRole('button', { name: /create.*project/i })).toBeVisible();
		await expect(authedPage.getByRole('button', { name: /join.*project/i })).toBeVisible();
	});

	test('should navigate to create project form', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Create Wizard', testInfo);

		// Create test event and attend via API
		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		await authedPage.goto('/');

		// Click create project button
		await authedPage.getByRole('button', { name: /create.*project/i }).click();

		// Should show create project form
		await expect(authedPage.locator('#project_name, input[name="name"]').first()).toBeVisible({ timeout: 10000 });
	});

	test('should navigate to join project form', async ({ authedPage, authedApi }, testInfo) => {
		const eventName = unique('Join Wizard', testInfo);

		// Create test event and attend via API
		const event = await createTestEvent(authedApi, { name: eventName });
		await attendEvent(authedApi, event.id);

		await authedPage.goto('/');

		// Click join project button
		await authedPage.getByRole('button', { name: /join.*project/i }).click();

		// Should show join project form with join code input
		await expect(
			authedPage.locator('input[placeholder*="code" i], #join_code').first()
		).toBeVisible({ timeout: 10000 });
	});
});
