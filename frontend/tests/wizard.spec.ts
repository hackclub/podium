import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { clickAndWaitForApi } from './utils/waiters';

test.describe('Wizard', () => {
	test('should complete start wizard flow', async ({ authedPage }, testInfo) => {
		const eventName = unique('Wizard Event', testInfo);

		// Create event first
		await authedPage.goto('/events/create');
		await authedPage.locator('#event_name').fill(eventName);
		await authedPage.locator('#event_description').fill('Test');
		await clickAndWaitForApi(authedPage, authedPage.getByRole('button', { name: /create event/i }), '/events', 'POST');

		// Navigate to home to see wizard
		await authedPage.goto('/');
		
		// Should see start wizard or dashboard
		await expect(authedPage.getByRole('heading', { name: /welcome/i }).first()).toBeVisible({ timeout: 10000 });
	});
});
