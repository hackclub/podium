import { test as base, request as apiRequest, expect } from '@playwright/test';

const API_BASE_URL = 'http://127.0.0.1:8000';

type AuthFixtures = {
	userEmail: string;
	token: string;
	api: import('@playwright/test').APIRequestContext;
	authedContext: import('@playwright/test').BrowserContext;
	authedPage: import('@playwright/test').Page;
};

export const test = base.extend<AuthFixtures>({
	// Unique email per worker (parallel isolation)
	userEmail: [
		async ({}, use, workerInfo) => {
			await use(`test+pw${workerInfo.workerIndex}@example.com`);
		},
		{ scope: 'worker' }
	],

	// Shared API context per worker
	api: [
		async ({}, use) => {
			const api = await apiRequest.newContext({ baseURL: API_BASE_URL });
			await use(api);
			await api.dispose();
		},
		{ scope: 'worker' }
	],

	// Get JWT token from backend (worker-scoped, reused across tests)
	token: [
		async ({ api, userEmail }, use, workerInfo) => {
			const displayName = `PW User ${workerInfo.workerIndex}`;
			
			// Create user via backend API
			const signupPayload = {
				email: userEmail,
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

			// Get magic link token and exchange for access token
			const { signMagicLinkToken } = await import('../helpers/jwt');
			const magicToken = signMagicLinkToken(userEmail, 30);
			
			const verifyResp = await api.get(`/verify?token=${magicToken}`);
			if (!verifyResp.ok()) {
				throw new Error(`Failed to get access token: ${verifyResp.status()}`);
			}

			const { access_token } = await verifyResp.json();
			await use(access_token);
		},
		{ scope: 'worker' }
	],

	// Authenticated browser context with token in localStorage
	authedContext: async ({ browser, token }, use, testInfo) => {
		const baseURL = String(testInfo.project.use.baseURL || 'http://127.0.0.1:4173');
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
		await use(context);
		await context.close();
	},

	// Authenticated page that waits for app init to complete
	authedPage: async ({ authedContext, token }, use) => {
		const page = await authedContext.newPage();
		
		// Navigate and wait for client-side auth validation to complete
		await page.goto('/');
		await page.waitForResponse(
			(res) => res.url().includes('/users/current') && res.request().method() === 'GET' && res.ok(),
			{ timeout: 30000 }
		).catch(() => {
			// If validation doesn't complete, continue anyway - token is in localStorage
			console.log('Auth validation timeout, continuing with localStorage token');
		});
		
		// Store token for test access
		(page as any)._authToken = token;
		
		await use(page);
		await page.close();
	}
});

export { expect };
