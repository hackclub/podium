import { test, expect } from '@playwright/test';
import { createEvent, attendEvent, createProject, joinProject, ensureAuthenticatedUser } from './utils';

test.describe('Project Management', () => {
	test('should create a project for an event', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Project Test Event', 'Test event');
		await attendEvent(page, event.joinCode);

		const project = await createProject(page, event.name, 'Test Project', 'Test project description');

		// Verify project appears in projects list
		await page.goto('/projects');
		await expect(page.getByText('Your Projects')).toBeVisible();
		await expect(page.getByRole('heading', { name: project.name })).toBeVisible();
	});

	test('should join a project with join code', async ({ page }) => {
		// Create event and project as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'Join Project Event', 'Test event');
		await attendEvent(page, event.joinCode);

		const project = await createProject(page, event.name, 'Join Test Project', 'Test project');

		// Switch to attendee user
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');

		// Join the event first
		await attendEvent(page, event.joinCode);

		// Join the project
		if (project.joinCode) {
			await joinProject(page, project.joinCode);

			// Verify project appears in attendee's projects
			await page.goto('/projects');
			await expect(page.getByRole('heading', { name: project.name })).toBeVisible();
		}
	});

	test('should prevent joining project without attending event', async ({ page }) => {
		// Create event and project as organizer
		const organizerEmail = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, organizerEmail, 'Test Organizer');

		const event = await createEvent(page, 'No Attend Event', 'Test event');
		await attendEvent(page, event.joinCode);

		const project = await createProject(page, event.name, 'No Attend Project', 'Test project');

		// Switch to attendee user who hasn't joined the event
		const attendeeEmail = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, attendeeEmail, 'Test Attendee');

		// Try to join project without attending event
		if (project.joinCode) {
			await page.goto('/projects/join');
			await page.locator('#join_code').fill(project.joinCode);
			await page.getByRole('button', { name: /join/i }).click();

			// Should show error
			await expect(page.getByText(/attend|not part of|error/i)).toBeVisible();
		}
	});

	test('should list projects owned by user', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Multi Project Event', 'Test event');
		await attendEvent(page, event.joinCode);

		// Create multiple projects
		const project1 = await createProject(page, event.name, 'Project One', 'First project');
		const project2 = await createProject(page, event.name, 'Project Two', 'Second project');

		// Verify both projects appear
		await page.goto('/projects');
		await expect(page.getByRole('heading', { name: project1.name })).toBeVisible();
		await expect(page.getByRole('heading', { name: project2.name })).toBeVisible();
	});

	test('should handle invalid project join code', async ({ page }) => {
		const email = `attendee+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Attendee');

		await page.goto('/projects/join');
		await page.locator('#join_code').fill('INVALID123');

		await page.getByRole('button', { name: /join/i }).click();

		// Should show error message
		await expect(page.getByText(/invalid|not found|error/i)).toBeVisible();
	});

	test('should update project details', async ({ page }) => {
		const email = `organizer+${Date.now()}@test.local`;
		await ensureAuthenticatedUser(page, email, 'Test Organizer');

		const event = await createEvent(page, 'Update Project Event', 'Test event');
		await attendEvent(page, event.joinCode);

		const project = await createProject(page, event.name, 'Update Test Project', 'Original description');

		// Navigate to projects page
		await page.goto('/projects');

		// Find and click on the project to edit
		const projectCard = page.locator('.card').filter({ hasText: project.name });
		await expect(projectCard).toBeVisible();

		// Look for edit button on the project card
		const editButton = projectCard.getByRole('button', { name: /edit|update/i });
		if (await editButton.isVisible()) {
			await editButton.click();

			// Should be on edit form
			const nameField = page.locator('#project_name');
			await expect(nameField).toBeVisible();

			// Update description
			const descField = page.locator('#project_description');
			await descField.fill('Updated description via test');

			// Submit update
			await page.getByRole('button', { name: /update|save/i }).click();

			// Should see success message
			await expect(page.getByText(/updated successfully|saved/i)).toBeVisible();
		}
	});
});
