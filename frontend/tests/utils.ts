import { Page, expect } from '@playwright/test';
import { signMagicLinkToken } from './helpers/jwt';

export interface EventInfo {
	name: string;
	joinCode: string;
	slug?: string;
}

export interface ProjectInfo {
	name: string;
	joinCode?: string;
}

export async function ensureAuthenticatedUser(
	page: Page,
	email: string,
	displayName: string = 'Test User'
): Promise<void> {

	// Navigate to login page
	await page.goto('/login');
	await expect(page.locator('#email')).toBeVisible({ timeout: 10000 });

	// Fill email and submit
	await page.locator('#email').fill(email);
	await page.getByRole('button', { name: /login|sign up/i }).click();

	// Wait for signup form or check if user exists
	const firstNameField = page.locator('#first_name');
	const needsSignup = await firstNameField.isVisible().catch(() => false);

	if (needsSignup) {
		// Fill signup form
		await firstNameField.fill(displayName.split(' ')[0]);
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

		// Wait for signup success
		await expect(page.getByText(/account created|success/i)).toBeVisible({ timeout: 10000 });
	}

	// Generate and use magic link token
	const token = signMagicLinkToken(email, 30);
	await page.goto(`/login?token=${token}`);

	// Wait for redirect to dashboard
	await page.waitForURL(/\/(events|projects|$)/, { timeout: 20000 });
}

export async function createEvent(
	page: Page,
	name: string,
	description: string = 'Test event description'
): Promise<EventInfo> {
	const timestamp = Date.now();
	const uniqueName = `${name} ${timestamp}`;

	// Navigate to create event page
	await page.goto('/events/create');
	await expect(page.locator('#event_name')).toBeVisible({ timeout: 15000 });

	// Fill form
	await page.locator('#event_name').fill(uniqueName);
	await page.locator('#event_description').fill(description);

	// Submit form
	await page.getByRole('button', { name: /create event/i }).click();

	// Wait for success message
	await expect(page.getByText(/created successfully|event created/i)).toBeVisible({ timeout: 15000 });

	// Navigate to events list to get join code
	await page.goto('/events');
	await expect(page.getByText('Events You Own')).toBeVisible({ timeout: 10000 });

	// Find the event row and extract join code
	const eventRow = page.locator('tr').filter({ hasText: uniqueName });
	await expect(eventRow).toBeVisible({ timeout: 10000 });

	const joinCodeBadge = eventRow.locator('.badge.badge-accent.font-mono');
	await expect(joinCodeBadge).toBeVisible({ timeout: 5000 });
	const joinCode = await joinCodeBadge.textContent();

	if (!joinCode) {
		throw new Error('Could not find join code for created event');
	}

	// Extract slug from event link
	const eventLink = eventRow.getByRole('link', { name: uniqueName });
	const href = await eventLink.getAttribute('href');
	const slug = href?.split('/').pop();

	return { name: uniqueName, joinCode: joinCode.trim(), slug };
}

export async function attendEvent(
	page: Page,
	joinCode: string,
	referral: string = 'Test referral'
): Promise<void> {
	await page.goto('/events/attend');
	await expect(page.locator('#join_code')).toBeVisible({ timeout: 10000 });

	await page.locator('#join_code').fill(joinCode);
	await page.locator('#referral').fill(referral);

	await page.getByRole('button', { name: /join.*event/i }).click();

	await expect(page.getByText(/joined.*successfully|success/i)).toBeVisible({ timeout: 15000 });
}

export async function createProject(
	page: Page,
	eventName: string,
	projectName: string,
	description: string = 'Test project description'
): Promise<ProjectInfo> {
	const timestamp = Date.now();
	const uniqueName = `${projectName} ${timestamp}`;

	await page.goto('/projects/create');
	await expect(page.locator('#project_name')).toBeVisible({ timeout: 15000 });

	// Fill form
	await page.locator('#project_name').fill(uniqueName);
	await page.locator('#project_description').fill(description);

	// Select event
	const eventSelect = page.locator('#event');
	await eventSelect.selectOption({ label: eventName });

	// Fill URLs
	await page.locator('#image_url').fill('https://example.com/image.png');
	await page.locator('#repo_url').fill('https://github.com/example/repo');
	await page.locator('#demo_url').fill('https://example.com/demo');

	// Submit
	await page.getByRole('button', { name: /ship it|create project/i }).click();

	// Wait for success
	await expect(page.getByText(/created successfully|project created/i)).toBeVisible({ timeout: 15000 });

	// Get join code from projects page
	await page.goto('/projects');
	await expect(page.getByText('Your Projects')).toBeVisible({ timeout: 10000 });

	const projectCard = page.locator('.card').filter({ hasText: uniqueName });
	await expect(projectCard).toBeVisible({ timeout: 10000 });

	// Try to extract join code if visible
	const joinCodeElement = projectCard.locator('text=/[A-Z0-9]{6}/');
	let joinCode: string | undefined;
	try {
		joinCode = await joinCodeElement.textContent();
	} catch {
		// Join code might not be visible on projects page
	}

	return { name: uniqueName, joinCode };
}

export async function joinProject(page: Page, joinCode: string): Promise<void> {
	await page.goto('/projects/join');
	await expect(page.locator('#join_code')).toBeVisible({ timeout: 10000 });

	await page.locator('#join_code').fill(joinCode);
	await page.getByRole('button', { name: /join/i }).click();

	await expect(page.getByText(/joined.*successfully|success/i)).toBeVisible({ timeout: 15000 });
}

export async function goToEventPage(page: Page, eventSlug: string): Promise<void> {
	await page.goto(`/events/${eventSlug}`);
	await expect(page.getByRole('heading')).toBeVisible({ timeout: 10000 });
}

export async function voteForProject(page: Page, eventSlug: string, projectName?: string): Promise<void> {
	await page.goto(`/events/${eventSlug}/rank`);
	await expect(page.getByText(/rank projects|vote/i)).toBeVisible({ timeout: 10000 });

	// Find first project card
	const projectCard = page.locator('.card').first();
	await expect(projectCard).toBeVisible({ timeout: 10000 });

	// Click to select project
	await projectCard.click();

	// Submit vote
	const submitButton = page.getByRole('button', { name: /submit vote|vote/i });
	await expect(submitButton).toBeEnabled({ timeout: 5000 });
	await submitButton.click();

	// Wait for success
	await expect(page.getByText(/voted|submitted|thanks/i)).toBeVisible({ timeout: 10000 });
}

export async function waitForElement(page: Page, selector: string, timeout = 10000): Promise<void> {
	await page.waitForSelector(selector, { timeout, state: 'visible' });
}

export async function waitForText(page: Page, text: string | RegExp, timeout = 10000): Promise<void> {
	await expect(page.getByText(text)).toBeVisible({ timeout });
}
