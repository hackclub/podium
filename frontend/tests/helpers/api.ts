import { APIRequestContext } from '@playwright/test';

const API_URL = process.env.PUBLIC_API_URL || 'http://127.0.0.1:8000';

export async function createEvent(
	api: APIRequestContext,
	data: { name: string; description: string }
) {
	const response = await api.post(`${API_URL}/events/`, { data });
	if (!response.ok()) {
		throw new Error(`Failed to create event: ${response.status()} ${await response.text()}`);
	}
	return await response.json();
}

export async function attendEvent(
	api: APIRequestContext,
	joinCode: string,
	referral?: string
) {
	const url = new URL(`${API_URL}/events/attend`);
	url.searchParams.set('join_code', joinCode);
	if (referral) url.searchParams.set('referral', referral);

	const response = await api.post(url.toString());
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
		event: string[];
		demo?: string;
		github_url?: string;
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

export async function voteForProject(
	api: APIRequestContext,
	eventId: string,
	projectId: string
) {
	const url = new URL(`${API_URL}/events/vote`);
	url.searchParams.set('event_id', eventId);
	url.searchParams.set('project_id', projectId);

	const response = await api.post(url.toString());
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
