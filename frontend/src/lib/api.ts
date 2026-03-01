import { PUBLIC_API_URL } from '$env/static/public';
import { getToken } from './auth';

const BASE = PUBLIC_API_URL || '/api';

class ApiError extends Error {
	status: number;
	constructor(status: number, message: string) {
		super(message);
		this.status = status;
	}
}

async function apiFetch<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
	const token = getToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string>)
	};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const res = await fetch(`${BASE}${path}`, { ...options, headers });

	if (!res.ok) {
		const body = await res.text();
		let message: string;
		try {
			message = JSON.parse(body).message || body;
		} catch {
			message = body;
		}
		throw new ApiError(res.status, message);
	}

	const text = await res.text();
	if (!text) return undefined as T;
	return JSON.parse(text) as T;
}

// ── Auth ───────────────────────────────────────────────────────────────

export function requestLogin(email: string, redirect?: string) {
	const qs = redirect ? `?redirect=${encodeURIComponent(redirect)}` : '';
	return apiFetch<{ message: string }>(`/auth/request-login${qs}`, {
		method: 'POST',
		body: JSON.stringify({ email })
	});
}

export function verifyToken(token: string) {
	return apiFetch<{ access_token: string }>(`/auth/verify?token=${encodeURIComponent(token)}`);
}

// ── Users ──────────────────────────────────────────────────────────────

export type ApiUser = {
	id: string;
	email: string;
	display_name: string;
	first_name: string;
	last_name: string;
	is_admin: boolean;
	is_superadmin: boolean;
	has_address: boolean;
	has_dob: boolean;
	has_phone: boolean;
};

export function getCurrentUser() {
	return apiFetch<ApiUser>('/users/current');
}

export function userExists(email: string) {
	return apiFetch<{ exists: boolean }>(`/users/exists?email=${encodeURIComponent(email)}`);
}

export function updateCurrentUser(data: {
	street_1?: string;
	street_2?: string;
	city?: string;
	state?: string;
	zip_code?: string;
	country?: string;
	dob?: string;
	first_name?: string;
	last_name?: string;
	phone?: string;
}) {
	return apiFetch<ApiUser>('/users/current', {
		method: 'PUT',
		body: JSON.stringify(data)
	});
}

export function createUser(data: { email: string; first_name: string; last_name?: string }) {
	return apiFetch<ApiUser>('/users', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

// ── Events ─────────────────────────────────────────────────────────────

export type ApiEvent = {
	id: string;
	name: string;
	slug: string;
	description: string;
	enabled: boolean;
	votable: boolean;
	voting_closed: boolean;
	leaderboard_enabled: boolean;
	demo_links_optional: boolean;
	ysws_checks_enabled: boolean;
	max_votes_per_user: number;
	feature_flags_csv: string;
	theme_name: string;
	theme_background: string;
	theme_font: string;
	theme_primary: string;
	theme_selected: string;
};

export function getOfficialEvents() {
	return apiFetch<ApiEvent[]>('/events/official');
}

export async function getEventBySlug(slug: string): Promise<string> {
	const res = await apiFetch<{ id: string }>(`/events/id/${encodeURIComponent(slug)}`);
	return res.id;
}

export function getEvent(eventId: string) {
	return apiFetch<ApiEvent>(`/events/${eventId}`);
}

export function getEventProjects(eventId: string, leaderboard = false) {
	const qs = leaderboard ? '?leaderboard=true' : '';
	return apiFetch<ApiProject[]>(`/events/${eventId}/projects${qs}`);
}

export function attendEvent(eventId: string) {
	return apiFetch<{ message: string; event_id: string }>(`/events/${eventId}/attend`, {
		method: 'POST'
	});
}

export function getMyVotes(eventId: string) {
	return apiFetch<string[]>(`/events/${eventId}/my-votes`);
}

export function vote(eventId: string, projectIds: string[]) {
	return apiFetch<{ message: string }>('/events/vote', {
		method: 'POST',
		body: JSON.stringify({ event: eventId, projects: projectIds })
	});
}

// ── Projects ───────────────────────────────────────────────────────────

export type ApiProjectCollaborator = {
	user_id: string;
	display_name: string;
};

export type ApiProject = {
	id: string;
	name: string;
	repo: string;
	image_url: string;
	demo: string;
	description: string;
	points: number;
	owner_id: string;
	owner_name: string;
	collaborators: ApiProjectCollaborator[];
};

export async function uploadScreenshot(file: File, eventSlug: string): Promise<string> {
	const token = getToken();
	const form = new FormData();
	form.append('file', file);
	const res = await fetch(
		`${BASE}/projects/upload-screenshot?event_slug=${encodeURIComponent(eventSlug)}`,
		{
			method: 'POST',
			headers: token ? { Authorization: `Bearer ${token}` } : {},
			body: form
		}
	);
	if (!res.ok) {
		const body = await res.text();
		let message: string;
		try { message = JSON.parse(body).message || body; } catch { message = body; }
		throw new ApiError(res.status, message);
	}
	const { url } = await res.json();
	return url;
}

export function getMyProjects() {
	return apiFetch<(ApiProject & { join_code: string; hours_spent: number; event_id: string })[]>('/projects/mine');
}

export type TeammateData = {
	email: string;
	first_name?: string;
	last_name?: string;
	phone?: string;
	street_1?: string;
	street_2?: string;
	city?: string;
	state?: string;
	zip_code?: string;
	country?: string;
	dob?: string;
};

export function lookupTeammate(email: string) {
	return apiFetch<{ found: boolean; missing_fields: string[] }>(
		`/users/lookup?email=${encodeURIComponent(email)}`
	);
}

export function createProject(data: {
	name: string;
	demo: string;
	repo: string;
	description: string;
	hours_spent: number;
	event_id: string;
	image_url?: string;
	teammates?: TeammateData[];
}) {
	return apiFetch<{ id: string }>('/projects', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export function getProject(projectId: string) {
	return apiFetch<ApiProject & { join_code: string; hours_spent: number; event_id: string }>(
		`/projects/${projectId}`
	);
}

export function updateProject(
	projectId: string,
	data: Partial<{ name: string; demo: string; repo: string; description: string; hours_spent: number; image_url: string }>
) {
	return apiFetch(`/projects/${projectId}`, {
		method: 'PUT',
		body: JSON.stringify(data)
	});
}

export function deleteProject(projectId: string) {
	return apiFetch(`/projects/${projectId}`, { method: 'DELETE' });
}

export function ownerAddCollaborator(projectId: string, data: TeammateData) {
	return apiFetch<ApiProjectCollaborator>(`/projects/${projectId}/collaborators`, {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export function ownerRemoveCollaborator(projectId: string, userId: string) {
	return apiFetch(`/projects/${projectId}/collaborators/${userId}`, { method: 'DELETE' });
}

// ── Admin Auth ─────────────────────────────────────────────────────────

export function requestAdminOtp(email: string) {
	return apiFetch<{ message: string }>('/auth/admin/request-otp', {
		method: 'POST',
		body: JSON.stringify({ email })
	});
}

export function verifyAdminOtp(email: string, code: string) {
	return apiFetch<{
		access_token: string;
		token_type: string;
		user: { id: string; email: string; display_name: string; is_admin: boolean };
	}>('/auth/admin/verify-otp', {
		method: 'POST',
		body: JSON.stringify({ email, code })
	});
}

// ── Admin: Events ──────────────────────────────────────────────────────

export type ApiAdminEvent = ApiEvent & {
	owner_id: string;
	poc_id: string | null;
	rm_id: string | null;
	feature_flags_csv: string;
	ysws_checks_enabled: boolean;
	attendee_count: number;
	project_count: number;
	vote_count: number;
};

export function adminListEvents() {
	return apiFetch<ApiAdminEvent[]>('/events/admin');
}

export function adminGetEvent(eventId: string) {
	return apiFetch<ApiAdminEvent>(`/events/admin/${eventId}`);
}

export function adminCreateEvent(data: {
	name: string;
	slug: string;
	description?: string;
	feature_flags_csv?: string;
	theme_name?: string;
	theme_background?: string;
	theme_font?: string;
	theme_primary?: string;
	theme_selected?: string;
	poc_id?: string | null;
	rm_id?: string | null;
}) {
	return apiFetch<ApiAdminEvent>('/events/admin/create', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export function adminUpdateEvent(
	eventId: string,
	data: Partial<{
		name: string;
		slug: string;
		description: string;
		enabled: boolean;
		votable: boolean;
		voting_closed: boolean;
		leaderboard_enabled: boolean;
		demo_links_optional: boolean;
		ysws_checks_enabled: boolean;
		feature_flags_csv: string;
		theme_name: string;
		theme_background: string;
		theme_font: string;
		theme_primary: string;
		theme_selected: string;
		poc_id: string | null;
		rm_id: string | null;
	}>
) {
	return apiFetch<ApiAdminEvent>(`/events/admin/${eventId}`, {
		method: 'PUT',
		body: JSON.stringify(data)
	});
}

export function adminDeleteEvent(eventId: string) {
	return apiFetch(`/events/admin/${eventId}`, { method: 'DELETE' });
}

export function adminSyncFromCockpit(eventId: string) {
	return apiFetch<{ message: string; event_id: string; attendees_synced: number }>(
		`/events/admin/${eventId}/sync-cockpit`,
		{ method: 'POST' }
	);
}

export function adminSyncEventToAirtable(eventId: string) {
	return apiFetch<{
		message: string;
		synced: number;
		total: number;
		errors?: string[];
	}>(`/events/admin/${eventId}/sync-airtable`, {
		method: 'POST'
	});
}

export type ApiAttendee = {
	id: string;
	user_id: string;
	email: string;
	display_name: string;
	has_project: boolean;
};

export function adminGetAttendees(eventId: string) {
	return apiFetch<ApiAttendee[]>(`/events/admin/${eventId}/attendees`);
}

export function adminAddAttendee(eventId: string, email: string) {
	return apiFetch<ApiAttendee>(`/events/admin/${eventId}/attendees`, {
		method: 'POST',
		body: JSON.stringify({ email })
	});
}

export function adminRemoveAttendee(eventId: string, userId: string) {
	return apiFetch(`/events/admin/${eventId}/attendees/${userId}`, { method: 'DELETE' });
}

export type ApiLeaderboardProject = ApiProject & {
	vote_count: number;
	manual_points: number;
	hours_spent: number;
};

export function adminGetLeaderboard(eventId: string) {
	return apiFetch<ApiLeaderboardProject[]>(`/events/admin/${eventId}/leaderboard`);
}

export function adminSetProjectPoints(eventId: string, projectId: string, points: number) {
	return apiFetch<{ message: string }>(`/events/admin/${eventId}/projects/${projectId}/points`, {
		method: 'PUT',
		body: JSON.stringify({ points })
	});
}

export type ApiEventStats = {
	total_attendees: number;
	submitted_count: number;
	missing_count: number;
	attendees: {
		user_id: string;
		email: string;
		display_name: string;
		has_project: boolean;
	}[];
	leaderboard: {
		id: string;
		name: string;
		image_url: string;
		description: string;
		owner_id: string;
		vote_count: number;
	}[];
};

export function adminGetEventStats(eventId: string) {
	return apiFetch<ApiEventStats>(`/events/admin/${eventId}/stats`);
}

// ── Admin: Projects ────────────────────────────────────────────────────

export function adminUpdateProject(
	projectId: string,
	data: Partial<{ name: string; demo: string; repo: string; description: string; hours_spent: number; image_url: string }>
) {
	return apiFetch(`/projects/admin/${projectId}`, {
		method: 'PUT',
		body: JSON.stringify(data)
	});
}

export function adminDeleteProject(projectId: string) {
	return apiFetch(`/projects/admin/${projectId}`, { method: 'DELETE' });
}

export function adminAddCollaborator(projectId: string, data: TeammateData) {
	return apiFetch<ApiProjectCollaborator>(`/projects/admin/${projectId}/collaborators`, {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export function adminRemoveCollaborator(projectId: string, userId: string) {
	return apiFetch(`/projects/admin/${projectId}/collaborators/${userId}`, { method: 'DELETE' });
}

// ── Campfire (superadmin) ───────────────────────────────────────────

// ── Campfire Dashboard (superadmin) ─────────────────────────────

export type CampfireDashboardEvent = {
	id: string;
	name: string;
	slug: string;
	attendee_count: number;
	project_count: number;
	shipper_count: number;
	ship_rate: number;
	checkin_count: number;
	scanned_day1_count: number;
	scanned_day2_count: number;
	scanned_either_day_count: number;
};

export type CampfireDashboard = {
	total_shippers: number;
	total_projects: number;
	total_attendees: number;
	total_checkins: number;
	total_scanned_either_day: number;
	events: CampfireDashboardEvent[];
};

export function adminGetCampfireDashboard() {
	return apiFetch<CampfireDashboard>('/events/admin/campfire/dashboard');
}

export type PublicDashboardEvent = {
	name: string;
	slug: string;
	attendee_count: number;
	project_count: number;
	shipper_count: number;
	ship_rate: number;
	checkin_count: number;
	scanned_day1_count: number;
	scanned_day2_count: number;
	scanned_either_day_count: number;
};

export type PublicDashboard = {
	total_shippers: number;
	total_projects: number;
	total_attendees: number;
	total_checkins: number;
	total_scanned_either_day: number;
	events: PublicDashboardEvent[];
};

export function getPublicDashboard() {
	return apiFetch<PublicDashboard>('/events/public/dashboard');
}

// ── Platform Settings (superadmin) ─────────────────────────────────

export type PlatformSettings = {
	github_validation_enabled: boolean;
	itch_validation_enabled: boolean;
};

export function adminGetPlatformSettings() {
	return apiFetch<PlatformSettings>('/events/admin/platform-settings');
}

export function adminUpdatePlatformSettings(data: Partial<PlatformSettings>) {
	return apiFetch<PlatformSettings>('/events/admin/platform-settings', {
		method: 'PUT',
		body: JSON.stringify(data),
	});
}

export type CockpitEvent = {
	id: string;
	name: string;
	displayName: string;
	format: string;
	city: string;
	country: string;
	status: string;
	numParticipants: number;
	estimatedAttendeesCount: number;
	percentSignup: number;
	hasVenue: boolean;
	pocName: string[];
	pocEmail: string[];
	rmName: string[];
	rmEmail: string[];
	already_imported: boolean;
};

export function adminGetCampfireEvents() {
	return apiFetch<CockpitEvent[]>('/events/admin/campfire/events');
}

export function adminImportCampfireEvent(cockpitEventId: string) {
	return apiFetch<{
		message: string;
		event_id: string;
		slug: string;
		attendees_imported: number;
		admins: string[];
	}>('/events/admin/campfire/import', {
		method: 'POST',
		body: JSON.stringify({ cockpit_event_id: cockpitEventId })
	});
}

export function adminSyncCampfireEvent(cockpitEventId: string) {
	return apiFetch<{
		message: string;
		event_id: string;
		slug: string;
		attendees_synced: number;
		disabled?: boolean;
		admins: string[];
	}>('/events/admin/campfire/sync', {
		method: 'POST',
		body: JSON.stringify({ cockpit_event_id: cockpitEventId })
	});
}

export function adminSyncAllCampfireEvents() {
	return apiFetch<{
		message: string;
		results: { id: string; name: string; synced: number; disabled?: boolean; error?: string }[];
	}>('/events/admin/campfire/sync-all', {
		method: 'POST'
	});
}

export function adminSyncProjectsToAirtable() {
	return apiFetch<{
		message: string;
		synced: number;
		total: number;
		errors?: string[];
	}>('/events/admin/campfire/sync-airtable', {
		method: 'POST'
	});
}

export type ItchValidationResult = {
	project_id: string;
	project_name: string;
	event_slug: string;
	demo_url: string;
	playable: boolean;
	reason: string;
};

export function adminValidateItchGames() {
	return apiFetch<{
		message: string;
		total: number;
		playable: number;
		not_playable: number;
		results: ItchValidationResult[];
	}>('/events/admin/campfire/validate-itch', {
		method: 'POST'
	});
}

export function adminImportAllActiveCampfireEvents() {
	return apiFetch<{
		message: string;
		results: { id: string; name: string; imported: number; error?: string }[];
	}>('/events/admin/campfire/import-all-active', {
		method: 'POST'
	});
}
