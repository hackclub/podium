import { test, expect, request as apiRequest } from '@playwright/test';
import { signMagicLinkToken, signAccessToken } from './helpers/jwt';

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
		const { token: organizerToken, api: organizerApi } = await createUserAndGetToken(
			organizerEmail,
			'Organizer User'
		);

		const organizerPage = await createAuthenticatedPage(browser, organizerToken, baseURL);

		// Create a new event
		const eventName = `Test Hackathon ${timestamp}`;
		await organizerPage.goto('/events/create');
		await organizerPage.locator('#event_name').fill(eventName);
		await organizerPage.locator('#event_description').fill('A test hackathon event');

		await Promise.all([
			organizerPage.waitForResponse(
				(r) => r.url().includes('/events') && r.request().method() === 'POST' && r.ok()
			),
			organizerPage.getByRole('button', { name: /create event/i }).click()
		]);

		await expect(organizerPage.getByText(/event created/i)).toBeVisible({ timeout: 10000 });

		// Navigate to events list and get the event
		await organizerPage.goto('/events');
		await organizerPage.waitForResponse(
			(r) => r.url().includes('/events') && r.request().method() === 'GET' && r.ok()
		);
		await organizerPage.getByRole('link', { name: eventName }).first().click();

		// Get join code from admin panel
		await expect(organizerPage.getByText(/admin panel/i)).toBeVisible({ timeout: 10000 });
		const joinCodeElement = await organizerPage.locator('.badge-accent.font-mono').first();
		const joinCode = await joinCodeElement.textContent();
		expect(joinCode).toBeTruthy();

		// Get event slug from URL
		const eventUrl = organizerPage.url();
		const eventSlug = eventUrl.split('/events/')[1]?.split('/')[0];

		// Enable voting and leaderboard via admin panel
		await organizerPage.getByRole('button', { name: /edit event/i }).click();
		await organizerPage.locator('#votable').check();
		await organizerPage.locator('#leaderboard_enabled').check();
		await organizerPage.locator('#demo_links_optional').check();

		await Promise.all([
			organizerPage.waitForResponse(
				(r) => r.url().includes('/events/') && r.request().method() === 'PUT' && r.ok()
			),
			organizerPage.getByRole('button', { name: /update event/i }).click()
		]);

		await expect(organizerPage.getByText(/event updated/i)).toBeVisible({ timeout: 10000 });

		// Create first project as organizer (need to attend first via UI)
		await organizerPage.goto('/events/attend');
		await organizerPage.locator('#join_code').fill(joinCode!);
		await organizerPage.locator('#referral').fill('Organizer self-join');

		await Promise.all([
			organizerPage.waitForResponse(
				(r) => r.url().includes('/attend') && r.request().method() === 'POST' && r.ok()
			),
			organizerPage.getByRole('button', { name: /join the event/i }).click()
		]);

		await expect(organizerPage.getByText(/joined event/i)).toBeVisible({ timeout: 10000 });

		await organizerPage.goto('/projects/create');
		await expect(organizerPage.locator('#project_name')).toBeVisible({ timeout: 10000 });
		await organizerPage.locator('#project_name').fill(`Project Alpha ${timestamp}`);
		await organizerPage.locator('#project_description').fill('First test project');
		await organizerPage.locator('#image_url').fill('https://example.com/image1.png');
		await organizerPage.locator('#repo_url').fill('https://github.com/test/project1');

		// Select event - focus triggers fetch, then wait for options to load
		await organizerPage.locator('#event').focus();
		await organizerPage.waitForTimeout(1000);
		await organizerPage.locator('#event').selectOption({ label: eventName });

		await Promise.all([
			organizerPage.waitForResponse(
				(r) => r.url().includes('/projects') && r.request().method() === 'POST' && r.ok()
			),
			organizerPage.getByRole('button', { name: /ship it/i }).click()
		]);

		await expect(organizerPage.getByText(/project created/i)).toBeVisible({ timeout: 10000 });

		// Create second project
		await organizerPage.locator('#project_name').fill(`Project Beta ${timestamp}`);
		await organizerPage.locator('#project_description').fill('Second test project');
		await organizerPage.locator('#image_url').fill('https://example.com/image2.png');
		await organizerPage.locator('#repo_url').fill('https://github.com/test/project2');
		await organizerPage.locator('#event').focus();
		await organizerPage.waitForTimeout(1000);
		await organizerPage.locator('#event').selectOption({ label: eventName });

		await Promise.all([
			organizerPage.waitForResponse(
				(r) => r.url().includes('/projects') && r.request().method() === 'POST' && r.ok()
			),
			organizerPage.getByRole('button', { name: /ship it/i }).click()
		]);

		await expect(organizerPage.getByText(/project created/i).first()).toBeVisible({ timeout: 10000 });

		// Sign out organizer
		await organizerPage.goto('/user');
		const logoutButton = organizerPage.getByRole('button', { name: /log\s*out|sign\s*out/i });
		if (await logoutButton.isVisible()) {
			await logoutButton.click();
		}
		await organizerPage.context().close();

		// ============================================
		// PART 2: Attendee joins event and votes
		// ============================================
		const attendeeEmail = `attendee+${timestamp}@test.local`;
		const { token: attendeeToken, api: attendeeApi } = await createUserAndGetToken(
			attendeeEmail,
			'Attendee User'
		);

		const attendeePage = await createAuthenticatedPage(browser, attendeeToken, baseURL);

		// Navigate to join link (simulating clicking join link)
		await attendeePage.goto(`/events/attend?join_code=${joinCode}`);
		await expect(attendeePage.getByText(/joined event/i)).toBeVisible({ timeout: 15000 });

		// Create a project as attendee
		await attendeePage.goto('/projects/create');
		await expect(attendeePage.locator('#project_name')).toBeVisible({ timeout: 10000 });
		await attendeePage.locator('#project_name').fill(`Attendee Project ${timestamp}`);
		await attendeePage.locator('#project_description').fill('Attendee test project');
		await attendeePage.locator('#image_url').fill('https://example.com/attendee.png');
		await attendeePage.locator('#repo_url').fill('https://github.com/test/attendee-project');

		await attendeePage.locator('#event').focus();
		await attendeePage.waitForTimeout(1000);
		await attendeePage.locator('#event').selectOption({ label: eventName });

		await Promise.all([
			attendeePage.waitForResponse(
				(r) => r.url().includes('/projects') && r.request().method() === 'POST' && r.ok()
			),
			attendeePage.getByRole('button', { name: /ship it/i }).click()
		]);

		await expect(attendeePage.getByText(/project created/i)).toBeVisible({ timeout: 10000 });

		// Navigate to event ranking page to verify it loads
		await attendeePage.goto(`/events/${eventSlug}/rank`);
		await expect(
			attendeePage.getByText(/you can vote for|already voted|submit vote/i).first()
		).toBeVisible({ timeout: 15000 });

		// Vote for projects via API (UI voting is complex with selection state)
		// First get the event projects to find one to vote for
		const projectsResp = await attendeeApi.get(
			`${API_BASE_URL}/events/${eventSlug.replace(eventSlug, '')}/projects?leaderboard=false`,
			{ headers: { Authorization: `Bearer ${attendeeToken}` } }
		);
		
		// Get event ID from the page URL or API
		const eventIdResp = await attendeeApi.get(`${API_BASE_URL}/events/id/${eventSlug}`);
		if (eventIdResp.ok()) {
			const eventId = (await eventIdResp.text()).replace(/"/g, '');
			
			// Get projects for this event
			const projResp = await attendeeApi.get(
				`${API_BASE_URL}/events/${eventId}/projects?leaderboard=false`,
				{ headers: { Authorization: `Bearer ${attendeeToken}` } }
			);
			
			if (projResp.ok()) {
				const projects = await projResp.json();
				// Find a project that isn't the attendee's own (should be Project Alpha or Beta)
				const voteableProject = projects.find((p: any) => 
					p.name.includes('Project Alpha') || p.name.includes('Project Beta')
				);
				
				if (voteableProject) {
					const voteResp = await attendeeApi.post(`${API_BASE_URL}/events/vote`, {
						headers: { 
							Authorization: `Bearer ${attendeeToken}`,
							'Content-Type': 'application/json'
						},
						data: { event: eventId, projects: [voteableProject.id] }
					});
					expect(voteResp.ok()).toBe(true);
				}
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

		// ============================================
		// PART 3: Organizer views admin and removes attendee
		// ============================================
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
	});
});
