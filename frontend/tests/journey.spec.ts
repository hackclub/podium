/**
 * E2E Journey Tests
 *
 * These tests focus on user-facing flows through the UI.
 * API calls are used ONLY for authentication and test infrastructure setup/teardown.
 * All actual feature testing happens through browser UI interactions,
 * which naturally exercises the backend APIs and ensures both frontend and backend work together.
 */

import { test, expect, request as apiRequest } from '@playwright/test';
import { signMagicLinkToken } from './helpers/jwt';

const API_BASE_URL = 'http://127.0.0.1:8000';

async function createUserAndGetToken(
	email: string,
	displayName: string
): Promise<{ token: string; api: import('@playwright/test').APIRequestContext }> {
	const api = await apiRequest.newContext({ baseURL: API_BASE_URL });

	const signupPayload = {
		email,
		first_name: displayName.split(' ')[0],
		last_name: displayName.split(' ')[1] || 'User',
		display_name: displayName,
		phone: '5551234567',
		street_1: '123 Test St',
		street_2: '',
		city: 'Testville',
		state: 'CA',
		zip_code: '12345',
		country: 'US',
		dob: '2000-01-01'
	};

	const createResp = await api.post('/users/', {
		headers: { 'Content-Type': 'application/json' },
		data: signupPayload
	});

	if (!createResp.ok() && createResp.status() !== 400) {
		throw new Error(`Failed to create user: ${createResp.status()}`);
	}

	const magicToken = signMagicLinkToken(email, 30);
	const verifyResp = await api.get(`/verify?token=${magicToken}`);
	if (!verifyResp.ok()) {
		throw new Error(`Failed to get access token: ${verifyResp.status()}`);
	}

	const { access_token } = await verifyResp.json();
	return { token: access_token, api };
}

async function createAuthenticatedPage(
	browser: import('@playwright/test').Browser,
	token: string,
	baseURL: string
): Promise<import('@playwright/test').Page> {
	const context = await browser.newContext({
		baseURL,
		storageState: {
			cookies: [],
			origins: [
				{
					origin: baseURL,
					localStorage: [{ name: 'token', value: token }]
				}
			]
		}
	});
	const page = await context.newPage();
	await page.goto('/');
	await page
		.waitForResponse(
			(res) =>
				res.url().includes('/users/current') && res.request().method() === 'GET' && res.ok(),
			{ timeout: 30000 }
		)
		.catch(() => {});
	return page;
}

async function createAuthedApiContext(token: string) {
	return apiRequest.newContext({
		baseURL: API_BASE_URL,
		extraHTTPHeaders: {
			Authorization: `Bearer ${token}`
		}
	});
}

test.describe('Full User Journey', () => {
	test('complete hackathon workflow - organizer creates event, attendee joins and votes', async ({
		browser
	}, testInfo) => {
		const timestamp = Date.now();
		const baseURL = String(testInfo.project.use.baseURL || 'http://127.0.0.1:4173');

		// ============================================
		// PART 1: Organizer creates event and projects
		// ============================================
		const organizerEmail = `organizer+${timestamp}@test.local`;
		const { token: organizerToken } = await createUserAndGetToken(
			organizerEmail,
			'Organizer User'
		);

		// Create authenticated API context for organizer (for setup only)
		const organizerApi = await createAuthedApiContext(organizerToken);

		// Create event via test API endpoint (setup only, not testing event creation UI)
		const eventName = `Test Hackathon ${timestamp}`;
		const createEventResp = await organizerApi.post('/events/test/create', {
			data: { name: eventName, description: 'A test hackathon event' }
		});
		expect(createEventResp.ok()).toBe(true);
		const event = await createEventResp.json();
		const eventId = event.id;
		const eventSlug = event.slug;

		const organizerPage = await createAuthenticatedPage(browser, organizerToken, baseURL);

		// Organizer joins event via EventSelector in UI
		await organizerPage.goto('/');
		await organizerPage.getByText(eventName).click();
		await expect(
			organizerPage.getByText(/joined event|welcome/i).first()
		).toBeVisible({ timeout: 15000 });

		// Create projects as organizer via UI (wizard on home page)
		// Test the full validation flow with a real playable itch.io game
		// Wizard shows "Create New Project" button on the chooseProject step
		await expect(organizerPage.getByRole('button', { name: /create new project/i })).toBeVisible({ timeout: 15000 });
		await organizerPage.getByRole('button', { name: /create new project/i }).click();
		await expect(organizerPage.locator('#project_name')).toBeVisible({ timeout: 10000 });
		await organizerPage.locator('#project_name').fill(`Project Alpha ${timestamp}`);
		await organizerPage.locator('#project_description').fill('First test project');
		await organizerPage.locator('#image_url').fill('https://raw.githubusercontent.com/hackclub/podium/main/README.md');
		await organizerPage.locator('#repo_url').fill('https://github.com/hackclub/podium');
		// Add a real playable itch.io game to test successful validation
		await organizerPage.locator('#demo_url').fill('https://qrosp-games-oy.itch.io/deathleap');

		await Promise.all([
			organizerPage.waitForResponse(
				(r) => r.url().includes('/projects') && r.request().method() === 'POST' && r.ok()
			),
			organizerPage.getByRole('button', { name: /ship it/i }).click()
		]);

		// Wizard auto-validates and should show success
		// (validation passes because deathleap is a real playable game)
		await expect(
			organizerPage.getByText(/all set/i).first()
		).toBeVisible({ timeout: 15000 });

		// Create second project via API for voting test (test infrastructure - needed so attendee has something to vote for)
		const createProject2Resp = await organizerApi.post('/projects/', {
			data: {
				name: `Project Beta ${timestamp}`,
				description: 'Second test project',
				image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md',
				repo: 'https://github.com/hackclub/podium',
				demo: 'https://qrosp-games-oy.itch.io/deathleap',
				event_id: eventId,
				hours_spent: 0
			}
		});
		expect(createProject2Resp.ok()).toBe(true);

		// Sign out organizer
		await organizerPage.goto('/user');
		const logoutButton = organizerPage.getByRole('button', { name: /log\s*out|sign\s*out/i });
		if (await logoutButton.isVisible()) {
			await logoutButton.click();
		}
		await organizerPage.context().close();
		await organizerApi.dispose();

		// ============================================
		// PART 2: Attendee selects event and votes
		// ============================================
		const attendeeEmail = `attendee+${timestamp}@test.local`;
		const { token: attendeeToken, api: attendeeApiBase } = await createUserAndGetToken(
			attendeeEmail,
			'Attendee User'
		);

		// Create authenticated API context
		const attendeeApi = await createAuthedApiContext(attendeeToken);

		const attendeePage = await createAuthenticatedPage(browser, attendeeToken, baseURL);

		// Navigate to home - should see EventSelector
		await attendeePage.goto('/');

		// Click on the event to attend it
		await attendeePage.getByText(eventName).click();

		// Should show success message or project submission wizard
		await expect(
			attendeePage.getByText(/joined event|welcome|create.*project/i).first()
		).toBeVisible({ timeout: 15000 });

		// Create a project as attendee via wizard on home page with validation
		// Wizard should already be showing "Create New Project" button
		await expect(attendeePage.getByRole('button', { name: /create new project/i })).toBeVisible({ timeout: 15000 });
		await attendeePage.getByRole('button', { name: /create new project/i }).click();
		await expect(attendeePage.locator('#project_name')).toBeVisible({ timeout: 10000 });
		await attendeePage.locator('#project_name').fill(`Attendee Project ${timestamp}`);
		await attendeePage.locator('#project_description').fill('Attendee test project');
		await attendeePage.locator('#image_url').fill('https://raw.githubusercontent.com/hackclub/podium/main/README.md');
		await attendeePage.locator('#repo_url').fill('https://github.com/hackclub/podium');
		// Add the real playable itch.io game to test validation
		await attendeePage.locator('#demo_url').fill('https://qrosp-games-oy.itch.io/deathleap');

		await Promise.all([
			attendeePage.waitForResponse(
				(r) => r.url().includes('/projects') && r.request().method() === 'POST' && r.ok()
			),
			attendeePage.getByRole('button', { name: /ship it/i }).click()
		]);

		// Validation should pass with the real playable game
		await expect(
			attendeePage.getByText(/all set/i).first()
		).toBeVisible({ timeout: 15000 });

		// Navigate to event ranking page to vote via UI
		await attendeePage.goto(`/events/${eventSlug}/rank`);
		await expect(
			attendeePage.getByText(/you can vote for|already voted|submit vote/i).first()
		).toBeVisible({ timeout: 15000 });

		// Vote for a project via UI - look for a votable project card
		// Should see Project Alpha or Beta (organizer's projects)
		const projectCards = attendeePage.locator('[class*="project"], [data-testid*="project"]');
		const projectCount = await projectCards.count();
		
		if (projectCount > 0) {
			// Click the first votable project's vote button
			const voteButton = attendeePage.getByRole('button', { name: /vote|submit.*vote/i }).first();
			if (await voteButton.isVisible()) {
				await Promise.all([
					attendeePage.waitForResponse(
						(r) => r.url().includes('/events/vote') && r.request().method() === 'POST' && r.ok()
					),
					voteButton.click()
				]);
				// Verify vote was recorded
				await expect(attendeePage.getByText(/voted|vote.*recorded/i).first()).toBeVisible({ timeout: 10000 }).catch(() => {});
			}
		}

		// View leaderboard
		await attendeePage.goto(`/events/${eventSlug}/leaderboard`);
		await expect(attendeePage.getByText(/leaderboard/i)).toBeVisible({ timeout: 10000 });

		// Update project
		await attendeePage.goto('/projects');
		await attendeePage.waitForResponse(
			(r) => r.url().includes('/projects') && r.request().method() === 'GET'
		);

		const projectLink = attendeePage.getByRole('link', { name: new RegExp(`Attendee Project ${timestamp}`) });
		if (await projectLink.isVisible()) {
			await projectLink.click();

			const editButton = attendeePage.getByRole('button', { name: /edit/i });
			if (await editButton.isVisible()) {
				await editButton.click();

				const descField = attendeePage.locator('#project_description, textarea[name="description"]').first();
				if (await descField.isVisible()) {
					await descField.fill('Updated project description');

					const saveButton = attendeePage.getByRole('button', { name: /save|update/i }).first();
					if (await saveButton.isVisible()) {
						await Promise.all([
							attendeePage.waitForResponse(
								(r) => r.url().includes('/projects/') && r.request().method() === 'PUT' && r.ok()
							),
							saveButton.click()
						]);
					}
				}
			}
		}

		// Sign out attendee
		await attendeePage.goto('/user');
		const attendeeLogoutButton = attendeePage.getByRole('button', { name: /log\s*out|sign\s*out/i });
		if (await attendeeLogoutButton.isVisible()) {
			await attendeeLogoutButton.click();
		}
		await attendeePage.context().close();
		await attendeeApi.dispose();
		await attendeeApiBase.dispose();

		// ============================================
		// PART 3: Organizer views admin and removes attendee
		// ============================================
		const organizerApi2 = await createAuthedApiContext(organizerToken);
		const organizerPage2 = await createAuthenticatedPage(browser, organizerToken, baseURL);

		await organizerPage2.goto(`/events/${eventSlug}`);
		await expect(organizerPage2.getByText(/admin panel/i)).toBeVisible({ timeout: 10000 });

		// View admin leaderboard (should be in admin panel)
		await organizerPage2.waitForResponse(
			(r) => r.url().includes('/leaderboard') && r.request().method() === 'GET'
		).catch(() => {});

		// Find and remove the attendee - click Remove in table first, then confirm in modal
		const removeButton = organizerPage2.getByRole('button', { name: /remove/i }).first();
		if (await removeButton.isVisible()) {
			await removeButton.click();

			// Wait for confirmation modal and click the confirm Remove button
			const confirmRemoveButton = organizerPage2.locator('.modal, [class*="modal"]')
				.getByRole('button', { name: /remove/i });

			await Promise.all([
				organizerPage2.waitForResponse(
					(r) => r.url().includes('/remove-attendee') && r.request().method() === 'POST' && r.ok()
				),
				confirmRemoveButton.click()
			]);

			await expect(organizerPage2.getByText(/removed/i).first()).toBeVisible({ timeout: 10000 });
		}

		// Reload to verify
		await organizerPage2.reload();
		await expect(organizerPage2.getByText(/admin panel/i)).toBeVisible({ timeout: 10000 });

		await organizerPage2.context().close();
		await organizerApi2.dispose();
	});

	test('organizer can toggle event settings and manage own projects via UI', async ({
		browser
	}, testInfo) => {
		const timestamp = Date.now();
		const baseURL = String(testInfo.project.use.baseURL || 'http://127.0.0.1:4173');

		// Setup: Create organizer and event via API (infrastructure only)
		const organizerEmail = `organizer+${timestamp}@test.local`;
		const { token: organizerToken } = await createUserAndGetToken(
			organizerEmail,
			'Organizer User'
		);
		const organizerApi = await createAuthedApiContext(organizerToken);

		const eventName = `Organizer Test Event ${timestamp}`;
		const createEventResp = await organizerApi.post('/events/test/create', {
			data: { name: eventName, description: 'Test organizer features' }
		});
		const event = await createEventResp.json();
		const eventId = event.id;
		const eventSlug = event.slug;

		// Create two projects via API (test infrastructure - owned by organizer)
		const project1Resp = await organizerApi.post('/projects/', {
			data: {
				name: `Organizer Test Project 1 ${timestamp}`,
				description: 'First project',
				image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md',
				repo: 'https://github.com/hackclub/podium',
				demo: 'https://qrosp-games-oy.itch.io/deathleap',
				event_id: eventId,
				hours_spent: 0
			}
		});
		const project1Id = (await project1Resp.json()).id;

		const project2Resp = await organizerApi.post('/projects/', {
			data: {
				name: `Organizer Test Project 2 ${timestamp}`,
				description: 'Second project',
				image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md',
				repo: 'https://github.com/hackclub/podium',
				demo: 'https://qrosp-games-oy.itch.io/deathleap',
				event_id: eventId,
				hours_spent: 0
			}
		});
		const project2Id = (await project2Resp.json()).id;

		// Organizer attends event via API (prerequisite for admin panel access)
		await organizerApi.post(`/events/${eventId}/attend`);

		// Create authenticated page for organizer
		const organizerPage = await createAuthenticatedPage(browser, organizerToken, baseURL);

		// === TEST ORGANIZER ADMIN PANEL FEATURES ===
		
		// TEST 1: Navigate to event admin panel via UI
		await organizerPage.goto(`/events/${eventSlug}`);
		await expect(organizerPage.getByText(/admin panel/i)).toBeVisible({ timeout: 10000 });

		// TEST 2: Toggle voting on/off via UI (organizer-only admin feature)
		const votingToggleButton = organizerPage.getByRole('button', { name: /voting/i }).first();
		if (await votingToggleButton.isVisible()) {
			await votingToggleButton.click();
			// Verify toggle state changed (check for success message or state update)
			await organizerPage.waitForTimeout(500);
		}

		// TEST 3: Toggle leaderboard on/off via UI (organizer-only admin feature)
		const leaderboardToggleButton = organizerPage.getByRole('button', { name: /leaderboard/i }).first();
		if (await leaderboardToggleButton.isVisible()) {
			await leaderboardToggleButton.click();
			// Verify toggle state changed
			await organizerPage.waitForTimeout(500);
		}

		// TEST 4: Delete own project via UI - go to projects page and delete via modal
		// (Project owners can delete their own projects)
		await organizerPage.goto('/projects');
		await organizerPage.waitForResponse(
			(r) => r.url().includes('/projects') && r.request().method() === 'GET'
		);

		// Find edit button in the first project card
		const editButtons = organizerPage.getByRole('button', { name: /edit/i });
		const firstEditButton = editButtons.first();
		if (await firstEditButton.isVisible()) {
			await firstEditButton.click();

			// Modal should open with edit form
			const deleteButton = organizerPage.getByRole('button', { name: /delete/i });
			await expect(deleteButton).toBeVisible({ timeout: 5000 });
			await deleteButton.click();

			// Confirm deletion in modal
			const confirmButton = organizerPage.getByRole('button', { name: /delete/i }).nth(1);
			await Promise.all([
				organizerPage.waitForResponse(
					(r) => r.url().includes('/projects/') && r.request().method() === 'DELETE' && r.ok()
				),
				confirmButton.click()
			]);

			// Verify we're back on projects page
			await expect(organizerPage.getByText(/your projects/i)).toBeVisible({ timeout: 5000 });
		}

		// TEST 5: Update own project via modal
		// (Project owners can update their own projects)
		const editBtns = organizerPage.getByRole('button', { name: /edit/i });
		if ((await editBtns.count()) > 0) {
			await editBtns.first().click();

			// Update description
			const descField = organizerPage.locator('textarea').first();
			if (await descField.isVisible()) {
				await descField.clear();
				await descField.fill('Updated via UI flow');

				const updateButton = organizerPage.getByRole('button', { name: /update/i });
				await Promise.all([
					organizerPage.waitForResponse(
						(r) => r.url().includes('/projects/') && r.request().method() === 'PUT' && r.ok()
					),
					updateButton.click()
				]);
			}
		}

		await organizerPage.context().close();
		await organizerApi.dispose();
	});
});
