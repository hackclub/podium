import type { APIRequestContext, APIResponse } from '@playwright/test';

const API_URL = process.env.PUBLIC_API_URL || 'http://127.0.0.1:8000';

/**
 * Throw a descriptive error if the response is not OK.
 * Used by helpers that want to fail-fast on unexpected errors.
 */
async function assertOk(response: APIResponse, context: string): Promise<APIResponse> {
	if (!response.ok()) {
		throw new Error(`${context}: ${response.status()} ${await response.text()}`);
	}
	return response;
}

// =============================================================================
// AUTH
// =============================================================================

/**
 * Trigger a magic link email. With LOOPS_API_KEY unset (dev), the backend just
 * logs the link. Requires the user to already exist.
 */
export async function requestLogin(api: APIRequestContext, email: string, redirect = '/') {
	const response = await api.post(`${API_URL}/request-login?redirect=${encodeURIComponent(redirect)}`, {
		data: { email }
	});
	return response;
}

// =============================================================================
// USERS
// =============================================================================

export async function userExists(api: APIRequestContext, email: string) {
	const response = await api.get(
		`${API_URL}/users/exists?email=${encodeURIComponent(email)}`
	);
	await assertOk(response, 'userExists');
	return response.json();
}

export async function getCurrentUser(api: APIRequestContext) {
	const response = await api.get(`${API_URL}/users/current`);
	await assertOk(response, 'getCurrentUser');
	return response.json();
}

export async function updateCurrentUser(api: APIRequestContext, data: Record<string, unknown>) {
	const response = await api.put(`${API_URL}/users/current`, { data });
	await assertOk(response, 'updateCurrentUser');
	return response.json();
}

export async function getUserPublic(api: APIRequestContext, userId: string) {
	const response = await api.get(`${API_URL}/users/${userId}`);
	await assertOk(response, 'getUserPublic');
	return response.json();
}

// =============================================================================
// EVENTS (public + authenticated)
// =============================================================================

export async function getOfficialEvents(api: APIRequestContext) {
	const response = await api.get(`${API_URL}/events/official`);
	await assertOk(response, 'getOfficialEvents');
	return response.json();
}

export async function getEvent(api: APIRequestContext, eventId: string) {
	const response = await api.get(`${API_URL}/events/${eventId}`);
	await assertOk(response, 'getEvent');
	return response.json();
}

export async function getEventIdBySlug(api: APIRequestContext, slug: string) {
	const response = await api.get(`${API_URL}/events/id/${slug}`);
	await assertOk(response, 'getEventIdBySlug');
	return response.json();
}

export async function getAttendingEvents(api: APIRequestContext) {
	const response = await api.get(`${API_URL}/events/`);
	await assertOk(response, 'getAttendingEvents');
	return response.json();
}

export async function getEventProjects(
	api: APIRequestContext,
	eventId: string,
	leaderboard = false
) {
	const response = await api.get(
		`${API_URL}/events/${eventId}/projects?leaderboard=${leaderboard}`
	);
	return response;
}

export async function attendEvent(api: APIRequestContext, eventId: string) {
	const response = await api.post(`${API_URL}/events/${eventId}/attend`);
	await assertOk(response, 'attendEvent');
	return response.json();
}

export async function voteForProjects(
	api: APIRequestContext,
	eventId: string,
	projectIds: string[]
) {
	const response = await api.post(`${API_URL}/events/vote`, {
		data: { event: eventId, projects: projectIds }
	});
	return response;
}

// =============================================================================
// EVENTS — test-only endpoints (enable_test_endpoints=true in backend config)
// =============================================================================

export async function createTestEvent(
	api: APIRequestContext,
	data: { name: string; description?: string }
) {
	const response = await api.post(`${API_URL}/events/test/create`, { data });
	await assertOk(response, 'createTestEvent');
	return response.json();
}

export async function cleanupTestData(api: APIRequestContext) {
	const response = await api.post(`${API_URL}/events/test/cleanup`);
	await assertOk(response, 'cleanupTestData');
	return response.json();
}

// =============================================================================
// PROJECTS
// =============================================================================

export async function createProject(
	api: APIRequestContext,
	data: {
		name: string;
		description: string;
		event_id: string;
		repo: string;
		image_url: string;
		demo?: string;
		hours_spent?: number;
	}
) {
	const response = await api.post(`${API_URL}/projects/`, { data });
	await assertOk(response, 'createProject');
	return response.json();
}

export async function joinProject(api: APIRequestContext, joinCode: string) {
	const url = new URL(`${API_URL}/projects/join`);
	url.searchParams.set('join_code', joinCode);
	const response = await api.post(url.toString());
	return response;
}

export async function updateProject(
	api: APIRequestContext,
	projectId: string,
	data: Record<string, unknown>
) {
	const response = await api.put(`${API_URL}/projects/${projectId}`, { data });
	return response;
}

export async function deleteProject(api: APIRequestContext, projectId: string) {
	const response = await api.delete(`${API_URL}/projects/${projectId}`);
	return response;
}

export async function getProject(api: APIRequestContext, projectId: string) {
	const response = await api.get(`${API_URL}/projects/${projectId}`);
	return response;
}

export async function getMyProjects(api: APIRequestContext) {
	const response = await api.get(`${API_URL}/projects/mine`);
	await assertOk(response, 'getMyProjects');
	return response.json();
}

export async function validateProject(api: APIRequestContext, projectId: string) {
	const url = new URL(`${API_URL}/projects/validate`);
	url.searchParams.set('project_id', projectId);
	const response = await api.post(url.toString());
	return response;
}

// =============================================================================
// ADMIN / EVENT-OWNER ENDPOINTS
// =============================================================================

export async function adminGetEvent(api: APIRequestContext, eventId: string) {
	const response = await api.get(`${API_URL}/events/admin/${eventId}`);
	return response;
}

export async function adminPatchEvent(
	api: APIRequestContext,
	eventId: string,
	data: Record<string, unknown>
) {
	const response = await api.patch(`${API_URL}/events/admin/${eventId}`, { data });
	return response;
}

export async function adminGetAttendees(api: APIRequestContext, eventId: string) {
	const response = await api.get(`${API_URL}/events/admin/${eventId}/attendees`);
	return response;
}

export async function adminRemoveAttendee(
	api: APIRequestContext,
	eventId: string,
	userId: string
) {
	const response = await api.post(`${API_URL}/events/admin/${eventId}/remove-attendee`, {
		data: { user_id: userId }
	});
	return response;
}

export async function adminGetLeaderboard(api: APIRequestContext, eventId: string) {
	const response = await api.get(`${API_URL}/events/admin/${eventId}/leaderboard`);
	return response;
}

export async function adminGetVotes(api: APIRequestContext, eventId: string) {
	const response = await api.get(`${API_URL}/events/admin/${eventId}/votes`);
	return response;
}

export async function adminGetReferrals(api: APIRequestContext, eventId: string) {
	const response = await api.get(`${API_URL}/events/admin/${eventId}/referrals`);
	return response;
}

/** Backwards-compat alias used by older specs. */
export const getLeaderboard = adminGetLeaderboard;
