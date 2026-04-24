// TODO: Re-enable after Sleepover event. The POC requested email login be
// disabled for the event, so the email/magic-link UI is currently commented
// out in /login. These tests will fail until it's restored.
import { test as base, expect } from '@playwright/test';

base.describe('Authentication', () => {
	base.skip('should sign up new user', async ({ page }) => {
		const timestamp = Date.now();
		const email = `signup+${timestamp}@example.com`;
		const displayName = 'Test Signup User';

		await page.goto('/login');
		await expect(page.locator('#email')).toBeVisible();

		await page.locator('#email').fill(email);
		await page.getByRole('button', { name: /login|sign up/i }).click();

		await expect(page.locator('#first_name')).toBeVisible();

		await page.locator('#first_name').fill(displayName.split(' ')[0]);
		await page.locator('#last_name').fill(displayName.split(' ')[1] || 'User');
		await page.locator('#display_name').fill(displayName);
		await page.locator('#phone').fill('5551234567');
		await page.locator('#street_1').fill('123 Test St');
		await page.locator('#city').fill('Testville');
		await page.locator('#state').fill('CA');
		await page.locator('#zip_code').fill('12345');
		await page.locator('#country').selectOption('US');
		await page.locator('#dob').fill('2000-01-01');

		await page.getByRole('button', { name: /login|sign up/i }).click();

		await expect(page.getByText(/magic link sent|account created/i)).toBeVisible();
	});
});
