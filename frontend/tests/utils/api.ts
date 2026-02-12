import type { APIRequestContext } from '@playwright/test';

const API_BASE_URL = 'http://127.0.0.1:8000';

export interface EventData {
	id: string;
	name: string;
	slug: string;
	description?: string;
}

export async function getMyEvents(api: APIRequestContext, token: string): Promise<EventData[]> {
	const response = await api.get(`${API_BASE_URL}/events/`, {
		headers: { Authorization: `Bearer ${token}` }
	});

	if (!response.ok()) {
		throw new Error(`Failed to get events: ${response.status()}`);
	}

	const data = await response.json();
	return (data.attending_events || []) as EventData[];
}

export async function getOfficialEvents(api: APIRequestContext): Promise<EventData[]> {
	const response = await api.get(`${API_BASE_URL}/events/official`);

	if (!response.ok()) {
		throw new Error(`Failed to get official events: ${response.status()}`);
	}

	return (await response.json()) as EventData[];
}

export async function getEventBySlug(
	api: APIRequestContext,
	token: string,
	slug: string
): Promise<EventData | null> {
	const idResp = await api.get(`${API_BASE_URL}/events/id/${slug}`);
	if (!idResp.ok()) return null;

	const eventId = await idResp.json();
	if (typeof eventId !== 'string') return null;

	const eventResp = await api.get(`${API_BASE_URL}/events/${eventId.replace(/"/g, '')}`, {
		headers: { Authorization: `Bearer ${token}` }
	});

	if (!eventResp.ok()) return null;
	return (await eventResp.json()) as EventData;
}

export function slugify(name: string): string {
	return name
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}
