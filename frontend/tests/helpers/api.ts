import type { APIRequestContext } from '@playwright/test';

const API_URL = process.env.PUBLIC_API_URL || 'http://127.0.0.1:8000';

/**
 * Create a test event via the test-only endpoint.
 * Requires enable_test_endpoints=true in backend settings.
 */
export async function createTestEvent(
	api: APIRequestContext,
	data: { name: string; description?: string }
) {
	const response = await api.post(`${API_URL}/events/test/create`, { data });
	if (!response.ok()) {
		throw new Error(`Failed to create test event: ${response.status()} ${await response.text()}`);
	}
	return await response.json();
}

/**
 * Get list of official events for the current series.
 */
export async function getOfficialEvents(api: APIRequestContext) {
	const response = await api.get(`${API_URL}/events/official`);
	if (!response.ok()) {
		throw new Error(`Failed to get official events: ${response.status()} ${await response.text()}`);
	}
	return await response.json();
}

/**
 * Attend an official event by ID.
 */
export async function attendEvent(api: APIRequestContext, eventId: string) {
	const response = await api.post(`${API_URL}/events/${eventId}/attend`);
	if (!response.ok()) {
		throw new Error(`Failed to attend event: ${response.status()} ${await response.text()}`);
	}
	return await response.json();
}

export async function createProject(
	api: APIRequestContext,
	data: {
		name: string;
		description: string;
		event_id: string;
		repo: string;
		image_url: string;
		demo?: string;
	}
) {
	const response = await api.post(`${API_URL}/projects/`, { data });
	if (!response.ok()) {
		throw new Error(`Failed to create project: ${response.status()} ${await response.text()}`);
	}
	return await response.json();
}

export async function joinProject(api: APIRequestContext, joinCode: string) {
	const url = new URL(`${API_URL}/projects/join`);
	url.searchParams.set('join_code', joinCode);

	const response = await api.post(url.toString());
	if (!response.ok()) {
		throw new Error(`Failed to join project: ${response.status()} ${await response.text()}`);
	}
	return await response.json();
}

export async function voteForProjects(
	api: APIRequestContext,
	eventId: string,
	projectIds: string[]
) {
	const response = await api.post(`${API_URL}/events/vote`, {
		data: { event: eventId, projects: projectIds }
	});
	if (!response.ok()) {
		throw new Error(`Failed to vote: ${response.status()} ${await response.text()}`);
	}
	return await response.json();
}

export async function getLeaderboard(api: APIRequestContext, eventId: string) {
	const response = await api.get(`${API_URL}/events/admin/${eventId}/leaderboard`);
	if (!response.ok()) {
		throw new Error(
			`Failed to get leaderboard: ${response.status()} ${await response.text()}`
		);
	}
	return await response.json();
}
