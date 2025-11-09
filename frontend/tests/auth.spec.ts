import { test, expect } from '@playwright/test';
import { ensureAuthenticatedUser } from './utils';

test.describe('Authentication', () => {
	test('should sign up new user', async ({ page }) => {
		const timestamp = Date.now();
		const email = `signup+${timestamp}@test.local`;
		const displayName = 'Test Signup User';

		await page.goto('/login');
		await expect(page.locator('#email')).toBeVisible();

		// Fill email and submit
		await page.locator('#email').fill(email);
		await page.getByRole('button', { name: /login|sign up/i }).click();

		// Wait for signup form to appear
		await expect(page.locator('#first_name')).toBeVisible();

		// Fill signup details
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

		// Submit signup
		await page.getByRole('button', { name: /login|sign up/i }).click();

		// Should see success message
		await expect(page.getByText(/account created|signed up|success/i)).toBeVisible();
	});

	test('should login existing user', async ({ page }) => {
		const timestamp = Date.now();
		const email = `login+${timestamp}@test.local`;
		const displayName = 'Test Login User';

		// First sign up the user
		await ensureAuthenticatedUser(page, email, displayName);

		// Clear auth state to simulate fresh login
		await page.evaluate(() => localStorage.clear());
		await page.context().clearCookies();

		// Navigate to login
		await page.goto('/login');
		await page.locator('#email').fill(email);
		await page.getByRole('button', { name: /login|sign up/i }).click();

		// Should not see signup form (user exists)
		await expect(page.locator('#first_name')).not.toBeVisible();

		// Should redirect to dashboard after magic link
		await page.waitForURL(/\/(events|projects|$)/);
	});

	test('should handle magic link authentication', async ({ page }) => {
		const timestamp = Date.now();
		const email = `magic+${timestamp}@test.local`;
		const displayName = 'Test Magic User';

		// Sign up user first
		await ensureAuthenticatedUser(page, email, displayName);

		// Clear auth state
		await page.evaluate(() => localStorage.clear());
		await page.context().clearCookies();

		// Navigate to login and fill email
		await page.goto('/login');
		await page.locator('#email').fill(email);
		await page.getByRole('button', { name: /login|sign up/i }).click();

		// Wait for redirect to dashboard
		await page.waitForURL(/\/(events|projects|$)/);

		// Verify we're authenticated
		await expect(page.locator('text=/welcome|dashboard|events|projects/i')).toBeVisible();
	});

	test('should redirect authenticated users away from login', async ({ page }) => {
		const timestamp = Date.now();
		const email = `redirect+${timestamp}@test.local`;
		const displayName = 'Test Redirect User';

		// Authenticate user
		await ensureAuthenticatedUser(page, email, displayName);

		// Try to visit login page
		await page.goto('/login');

		// Should redirect away from login page
		await page.waitForURL(/\/(events|projects|$)/);
		expect(page.url()).not.toContain('/login');
	});

	test('should sign out user', async ({ page }) => {
		const timestamp = Date.now();
		const email = `signout+${timestamp}@test.local`;
		const displayName = 'Test Sign Out User';

		// Authenticate user
		await ensureAuthenticatedUser(page, email, displayName);

		// Verify we're logged in
		await expect(page.locator('text=/welcome|dashboard|events|projects/i')).toBeVisible();

		// Look for sign out button/link
		const signOutButton = page.getByRole('button', { name: /sign out|logout/i });
		if (await signOutButton.isVisible()) {
			await signOutButton.click();

			// Should redirect to login page
			await page.waitForURL(/\/login/);
			expect(page.url()).toContain('/login');
		} else {
			// Try alternative sign out methods
			const signOutLink = page.getByRole('link', { name: /sign out|logout/i });
			if (await signOutLink.isVisible()) {
				await signOutLink.click();

				// Should redirect to login page
				await page.waitForURL(/\/login/);
				expect(page.url()).toContain('/login');
			}
		}
	});
});
