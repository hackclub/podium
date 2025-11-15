import { APIRequestContext } from '@playwright/test';

const API_BASE_URL = 'http://127.0.0.1:8000';

export interface EventData {
	id: string;
	name: string;
	slug: string;
	join_code: string;
}

export async function getMyEvents(api: APIRequestContext, token: string): Promise<EventData[]> {
	const response = await api.get(`${API_BASE_URL}/events/`, {
		headers: { Authorization: `Bearer ${token}` }
	});
	
	if (!response.ok()) {
		throw new Error(`Failed to get events: ${response.status()}`);
	}
	
	const data = await response.json();
	return (data.owned || []) as EventData[];
}

export async function getEventBySlug(api: APIRequestContext, token: string, slug: string): Promise<EventData | null> {
	const idResp = await api.get(`${API_BASE_URL}/events/id/${slug}`);
	if (!idResp.ok()) return null;
	
	const eventId = await idResp.json();
	if (typeof eventId !== 'string') return null;
	
	const eventResp = await api.get(`${API_BASE_URL}/events/admin/${eventId}`, {
		headers: { Authorization: `Bearer ${token}` }
	});
	
	if (!eventResp.ok()) return null;
	return await eventResp.json() as EventData;
}

export function slugify(name: string): string {
	return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}
