import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import { clickAndWaitForApi } from './utils/waiters';

test.describe('Core Functionality', () => {
	test('should create event', async ({ authedPage }, testInfo) => {
		const eventName = unique('Test Event', testInfo);

		await authedPage.goto('/events/create');
		await authedPage.locator('#event_name').fill(eventName);
		await authedPage.locator('#event_description').fill('Test description');
		await clickAndWaitForApi(authedPage, authedPage.getByRole('button', { name: /create event/i }), '/events', 'POST');

		await expect(authedPage.getByText('Event created successfully')).toBeVisible({ timeout: 10000 });
	});

	test('should list owned events', async ({ authedPage }, testInfo) => {
		const eventName = unique('List Test', testInfo);

		await authedPage.goto('/events/create');
		await authedPage.locator('#event_name').fill(eventName);
		await authedPage.locator('#event_description').fill('Test');
		await clickAndWaitForApi(authedPage, authedPage.getByRole('button', { name: /create event/i }), '/events', 'POST');

		await authedPage.goto('/events');
		await authedPage.waitForResponse(r => r.url().includes('/events') && r.request().method() === 'GET' && r.ok());
		await expect(authedPage.getByRole('link', { name: eventName }).first()).toBeVisible({ timeout: 10000 });
	});

	test('should view event details', async ({ authedPage }, testInfo) => {
		const eventName = unique('Details Test', testInfo);

		await authedPage.goto('/events/create');
		await authedPage.locator('#event_name').fill(eventName);
		await authedPage.locator('#event_description').fill('Test');
		await clickAndWaitForApi(authedPage, authedPage.getByRole('button', { name: /create event/i }), '/events', 'POST');

		await authedPage.goto('/events');
		await authedPage.waitForResponse(r => r.url().includes('/events') && r.request().method() === 'GET' && r.ok());
		await authedPage.getByRole('link', { name: eventName }).first().click();

		await expect(authedPage.getByText(/admin panel|manage event/i).first()).toBeVisible({ timeout: 10000 });
	});

	test('should see leaderboard link', async ({ authedPage }, testInfo) => {
		const eventName = unique('Leaderboard Test', testInfo);

		await authedPage.goto('/events/create');
		await authedPage.locator('#event_name').fill(eventName);
		await authedPage.locator('#event_description').fill('Test');
		await clickAndWaitForApi(authedPage, authedPage.getByRole('button', { name: /create event/i }), '/events', 'POST');

		await authedPage.goto('/events');
		await authedPage.waitForResponse(r => r.url().includes('/events') && r.request().method() === 'GET' && r.ok());
		await authedPage.getByRole('link', { name: eventName }).first().click();

		await expect(authedPage.locator('a[href*="/leaderboard"]').first()).toBeVisible({ timeout: 10000 });
	});
});
