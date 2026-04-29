/**
 * Superadmin fixture — extends the base auth fixture with a worker-scoped
 * superadmin user. One user per worker, promoted once, reused across tests.
 *
 * Email pattern: admin+sa{N}@test.local — matches the cleanup SQL's 'admin+%@test.local'
 * so it's reaped by global teardown automatically.
 */

import { request as apiRequest } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';
import { test as authTest, expect } from './auth';
import { signMagicLinkToken } from '../helpers/jwt';
import { promoteSuperadmin } from '../helpers/api';

const API_BASE_URL = 'http://127.0.0.1:8000';

const DEFAULT_PII = {
	phone: '5551234567',
	street_1: '123 SA St',
	street_2: '',
	city: 'SAville',
	state: 'CA',
	zip_code: '12345',
	country: 'US',
	dob: '2000-01-01',
};

type SuperadminWorkerFixtures = {
	superadminToken: string;
	superadminApi: APIRequestContext;
};

export const test = authTest.extend<{}, SuperadminWorkerFixtures>({
	superadminToken: [
		async ({}, use, workerInfo) => {
			const email = `admin+sa${workerInfo.workerIndex}@test.local`;
			const api = await apiRequest.newContext({ baseURL: API_BASE_URL });

			// Create user — 400 means already exists from a prior run, which is fine.
			const signup = await api.post('/users/', {
				headers: { 'X-Turnstile-Token': 'e2e-test' },
				data: {
					email,
					first_name: 'SA',
					last_name: `Worker${workerInfo.workerIndex}`,
					display_name: `SA ${workerInfo.workerIndex}`,
					...DEFAULT_PII,
				},
			});
			if (!signup.ok() && signup.status() !== 400) {
				throw new Error(`Failed to create superadmin user: ${signup.status()} ${await signup.text()}`);
			}

			const magicToken = signMagicLinkToken(email, 30);
			const verify = await api.get(`/verify?token=${encodeURIComponent(magicToken)}`);
			if (!verify.ok()) throw new Error(`Failed to verify superadmin token: ${verify.status()}`);
			const { access_token } = await verify.json();
			await api.dispose();

			// Promote via authenticated context
			const authedApi = await apiRequest.newContext({
				baseURL: API_BASE_URL,
				extraHTTPHeaders: { Authorization: `Bearer ${access_token}` },
			});
			await promoteSuperadmin(authedApi);
			await authedApi.dispose();

			await use(access_token);
		},
		{ scope: 'worker' },
	],

	superadminApi: [
		async ({ superadminToken }, use) => {
			const api = await apiRequest.newContext({
				baseURL: API_BASE_URL,
				extraHTTPHeaders: { Authorization: `Bearer ${superadminToken}` },
			});
			await use(api);
			await api.dispose();
		},
		{ scope: 'worker' },
	],
});

export { expect };
