import { request as apiRequest } from '@playwright/test';
import type { APIRequestContext } from '@playwright/test';
import { signMagicLinkToken } from './jwt';

const API_BASE_URL = process.env.PUBLIC_API_URL || 'http://127.0.0.1:8000';

const DEFAULT_ADDRESS = {
	phone: '5551234567',
	street_1: '123 Test St',
	street_2: '',
	city: 'Testville',
	state: 'CA',
	zip_code: '12345',
	country: 'US',
	dob: '2000-01-01'
};

/**
 * Create a user via the public signup endpoint and exchange a signed magic-link
 * token for an access JWT. Returns both the token and an authenticated API
 * request context bound to the backend.
 *
 * Email pattern should start with `test+pw`, `organizer+`, `attendee+`, or
 * `admin+` so the /events/test/cleanup endpoint can reap them.
 */
export async function createUserAndGetToken(
	email: string,
	displayName: string
): Promise<{ token: string; api: APIRequestContext; authedApi: APIRequestContext }> {
	const api = await apiRequest.newContext({ baseURL: API_BASE_URL });

	const [firstName, ...rest] = displayName.split(' ');
	const lastName = rest.join(' ') || 'User';

	const signupResp = await api.post('/users/', {
		headers: { 'Content-Type': 'application/json', 'X-Turnstile-Token': 'e2e-test' },
		data: {
			email,
			first_name: firstName,
			last_name: lastName,
			display_name: displayName,
			...DEFAULT_ADDRESS
		}
	});

	// 400 means "user already exists" — fine, we can still log in.
	if (!signupResp.ok() && signupResp.status() !== 400) {
		throw new Error(
			`Failed to create user ${email}: ${signupResp.status()} ${await signupResp.text()}`
		);
	}

	const magicToken = signMagicLinkToken(email, 30);
	const verifyResp = await api.get(`/verify?token=${encodeURIComponent(magicToken)}`);
	if (!verifyResp.ok()) {
		throw new Error(`Failed to verify token for ${email}: ${verifyResp.status()}`);
	}
	const { access_token } = await verifyResp.json();

	const authedApi = await apiRequest.newContext({
		baseURL: API_BASE_URL,
		extraHTTPHeaders: { Authorization: `Bearer ${access_token}` }
	});

	return { token: access_token, api, authedApi };
}

/**
 * Build a unique email for a secondary test user. Uses a prefix that matches
 * the cleanup endpoint's LIKE patterns.
 */
export function secondaryUserEmail(prefix: 'organizer' | 'attendee' | 'admin', tag: string): string {
	return `${prefix}+${tag}@test.local`;
}
