import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { clickAndWaitForApi } from './utils/waiters';

test.describe('Permissions', () => {
	test('should protect event admin features', async ({ authedPage }, testInfo) => {
		const eventName = unique('Permission Test', testInfo);

		await authedPage.goto('/events/create');
		await authedPage.locator('#event_name').fill(eventName);
		await authedPage.locator('#event_description').fill('Test');
		await clickAndWaitForApi(authedPage, authedPage.getByRole('button', { name: /create event/i }), '/events', 'POST');

		await authedPage.goto('/events');
		await authedPage.getByRole('link', { name: eventName }).click();

		// Should see admin controls as owner
		await expect(authedPage.getByText(/admin panel|manage event/i).first()).toBeVisible({ timeout: 10000 });
	});
});
