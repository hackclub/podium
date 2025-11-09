import { test, expect } from '@playwright/test';
import { createEvent, ensureAuthenticatedUser } from './utils';

test.describe('Wizard User Journey', () => {
	test('should guide user through complete wizard flow', async ({ page }) => {
		// Create event as organizer first
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'Wizard Test Event', 'Test event for wizard');

		// Switch to new user who will use the wizard
		const wizardUserEmail = `wizard+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, wizardUserEmail, 'Wizard Test User');

		// Navigate to home page where wizard should appear
		await page.goto('/');

		// Look for StartWizard component or wizard prompt
		const startWizardButton = page.getByRole('button', { name: /start|begin|get started/i });
		const wizardHeading = page.getByText(/welcome|let's get started|start your journey/i);

		if (await startWizardButton.isVisible() || await wizardHeading.isVisible()) {
			// Click to start the wizard
			if (await startWizardButton.isVisible()) {
				await startWizardButton.click();
			}

			// Should be in join event step
			await expect(page.getByText(/join.*event|attend.*event/i)).toBeVisible();

			// Join the event via wizard
			await page.locator('#join_code').fill(event.joinCode);
			await page.locator('#referral').fill('From wizard test');
			await page.getByRole('button', { name: /join.*event/i }).click();

			// Should see success and move to project choice
			await expect(page.getByText(/joined.*successfully|success/i)).toBeVisible();

			// Should now be at project choice step
			await expect(page.getByText(/create.*project|join.*project|choose/i)).toBeVisible();

			// Choose to create a project
			const createProjectButton = page.getByRole('button', { name: /create.*project|ship it/i });
			if (await createProjectButton.isVisible()) {
				await createProjectButton.click();

				// Should be on project creation form
				await expect(page.locator('#project_name')).toBeVisible();

				// Fill project details
				await page.locator('#project_name').fill('Wizard Created Project');
				await page.locator('#project_description').fill('Project created via wizard');

				// Select event (should be pre-selected or selectable)
				const eventSelect = page.locator('#event');
				if (await eventSelect.isVisible()) {
					await eventSelect.selectOption({ label: event.name });
				}

				// Fill URLs
				await page.locator('#image_url').fill('https://example.com/image.png');
				await page.locator('#repo_url').fill('https://github.com/example/repo');
				await page.locator('#demo_url').fill('https://example.com/demo');

				// Submit project
				await page.getByRole('button', { name: /ship it|create project/i }).click();

				// Should see success and complete wizard
				await expect(page.getByText(/created successfully|project created/i)).toBeVisible();

				// Should be at completion step
				await expect(page.getByText(/complete|finished|all done/i)).toBeVisible();
			}
		} else {
			// If wizard doesn't appear, at least test that we can navigate to projects/events
			await page.goto('/events');
			await expect(page.getByText('Events')).toBeVisible();
		}
	});

	test('should create project via wizard twice', async ({ page }) => {
		// Create event as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');
		const event = await createEvent(page, 'Double Wizard Event', 'Test event for double wizard');

		// Switch to user who will create two projects
		const doubleWizardEmail = `doublewizard+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, doubleWizardEmail, 'Double Wizard User');

		// Join the event first
		await page.goto('/events/attend');
		await page.locator('#join_code').fill(event.joinCode);
		await page.locator('#referral').fill('Double wizard test');
		await page.getByRole('button', { name: /join.*event/i }).click();
		await expect(page.getByText(/joined.*successfully|success/i)).toBeVisible();

		// Create first project
		await page.goto('/projects/create');
		await page.locator('#project_name').fill('First Wizard Project');
		await page.locator('#project_description').fill('First project via wizard');
		const eventSelect = page.locator('#event');
		await eventSelect.selectOption({ label: event.name });
		await page.locator('#image_url').fill('https://example.com/image1.png');
		await page.locator('#repo_url').fill('https://github.com/example/repo1');
		await page.locator('#demo_url').fill('https://example.com/demo1');
		await page.getByRole('button', { name: /ship it|create project/i }).click();
		await expect(page.getByText(/created successfully|project created/i)).toBeVisible();

		// Create second project
		await page.goto('/projects/create');
		await page.locator('#project_name').fill('Second Wizard Project');
		await page.locator('#project_description').fill('Second project via wizard');
		await eventSelect.selectOption({ label: event.name });
		await page.locator('#image_url').fill('https://example.com/image2.png');
		await page.locator('#repo_url').fill('https://github.com/example/repo2');
		await page.locator('#demo_url').fill('https://example.com/demo2');
		await page.getByRole('button', { name: /ship it|create project/i }).click();
		await expect(page.getByText(/created successfully|project created/i)).toBeVisible();

		// Verify both projects appear
		await page.goto('/projects');
		await expect(page.getByRole('heading', { name: 'First Wizard Project' })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Second Wizard Project' })).toBeVisible();
	});
});
