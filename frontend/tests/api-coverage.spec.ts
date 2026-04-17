/**
 * API Endpoint Coverage
 *
 * Every backend HTTP endpoint is exercised in this file at least once — success
 * path when practical, plus common error paths where they inform route correctness
 * (e.g. 404 on unknown IDs, 403 on wrong actor). These tests run at the API layer
 * so they're fast and stable; UI-level verification lives in the other specs.
 *
 * When a new endpoint is added to backend/podium/routers/*.py, add a case here.
 */

import { test, expect } from './fixtures/auth';
import { unique } from './utils/data';
import {
	adminGetAttendees,
	adminGetEvent,
	adminGetLeaderboard,
	adminGetReferrals,
	adminGetVotes,
	adminPatchEvent,
	adminRemoveAttendee,
	attendEvent,
	createProject,
	createTestEvent,
	deleteProject,
	getAttendingEvents,
	getCurrentUser,
	getEvent,
	getEventIdBySlug,
	getEventProjects,
	getMyProjects,
	getOfficialEvents,
	getProject,
	getUserPublic,
	joinProject,
	requestLogin,
	updateCurrentUser,
	updateProject,
	userExists,
	validateProject,
	voteForProjects
} from './helpers/api';
import { createUserAndGetToken, secondaryUserEmail } from './helpers/users';

const BAD_UUID = '00000000-0000-0000-0000-000000000000';

test.describe('API coverage — AUTH router', () => {
	test('POST /request-login succeeds for an existing user', async ({
		authedApi,
		userEmail
	}) => {
		const resp = await requestLogin(authedApi, userEmail);
		// No LOOPS key in dev => endpoint returns 200 with no body
		expect(resp.ok()).toBe(true);
	});

	test('POST /request-login returns 404 for an unknown user', async ({ authedApi }, testInfo) => {
		// @example.com is the reserved documentation TLD — EmailStr accepts it.
		const unknown = `nobody+${Date.now()}-w${testInfo.workerIndex}@example.com`;
		const resp = await requestLogin(authedApi, unknown);
		expect(resp.status()).toBe(404);
	});

	// GET /verify is exercised in the `token` fixture for every worker, so it is
	// implicitly covered before any test runs.
});

test.describe('API coverage — USERS router', () => {
	test('GET /users/exists reports existing + missing users', async ({
		authedApi,
		userEmail
	}, testInfo) => {
		const present = await userExists(authedApi, userEmail);
		expect(present.exists).toBe(true);

		// /users/exists validates with EmailStr, which rejects .local as a reserved
		// TLD. Use @example.com (reserved documentation TLD) instead.
		const missingEmail = `nobody+${Date.now()}-w${testInfo.workerIndex}@example.com`;
		const missing = await userExists(authedApi, missingEmail);
		expect(missing.exists).toBe(false);
	});

	test('GET /users/current returns the authenticated user', async ({
		authedApi,
		userEmail
	}) => {
		const me = await getCurrentUser(authedApi);
		expect(me.email).toBe(userEmail);
		expect(typeof me.id).toBe('string');
	});

	test('PUT /users/current updates mutable profile fields', async ({
		authedApi
	}, testInfo) => {
		const newDisplayName = unique('Renamed', testInfo);
		const updated = await updateCurrentUser(authedApi, { display_name: newDisplayName });
		expect(updated.display_name).toBe(newDisplayName);

		const again = await getCurrentUser(authedApi);
		expect(again.display_name).toBe(newDisplayName);
	});

	test('GET /users/{user_id} returns a public profile', async ({ api, authedApi }) => {
		const me = await getCurrentUser(authedApi);
		const pub = await getUserPublic(api, me.id);
		expect(pub.id).toBe(me.id);
		expect(pub).toHaveProperty('display_name');
		// Public schema must not leak PII
		expect(pub).not.toHaveProperty('email');
		expect(pub).not.toHaveProperty('phone');
	});

	test('POST /users/ rejects duplicate signups', async ({ api, userEmail }) => {
		const resp = await api.post('/users/', {
			headers: { 'Content-Type': 'application/json' },
			data: {
				email: userEmail,
				first_name: 'Dup',
				last_name: 'User'
			}
		});
		expect(resp.status()).toBe(400);
	});
});

test.describe('API coverage — EVENTS router', () => {
	test('GET /events/official lists events in the active series', async ({
		authedApi
	}, testInfo) => {
		const name = unique('Official List', testInfo);
		const event = await createTestEvent(authedApi, { name });

		const events = await getOfficialEvents(authedApi);
		expect(Array.isArray(events)).toBe(true);
		expect(events.some((e: { id: string }) => e.id === event.id)).toBe(true);
	});

	test('GET /events/{event_id} returns the event and 404s on unknown IDs', async ({
		authedApi
	}, testInfo) => {
		const name = unique('GetById', testInfo);
		const event = await createTestEvent(authedApi, { name });

		const fetched = await getEvent(authedApi, event.id);
		expect(fetched.id).toBe(event.id);
		expect(fetched.name).toBe(name);

		const missing = await authedApi.get(`/events/${BAD_UUID}`);
		expect(missing.status()).toBe(404);
	});

	test('GET /events/ returns events the user attends', async ({ authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Attending', testInfo) });
		await attendEvent(authedApi, event.id);

		const mine = await getAttendingEvents(authedApi);
		expect(mine.attending_events.some((e: { id: string }) => e.id === event.id)).toBe(true);
	});

	test('GET /events/id/{slug} maps slug to ID', async ({ authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('SlugLookup', testInfo) });
		const idResp = await authedApi.get(`/events/id/${event.slug}`);
		expect(idResp.ok()).toBe(true);
		const body = await idResp.text();
		// endpoint returns a bare JSON-encoded string
		expect(body.replace(/"/g, '')).toBe(event.id);

		// Also via helper
		const viaHelper = await getEventIdBySlug(authedApi, event.slug);
		expect(viaHelper).toBe(event.id);
	});

	test('GET /events/{event_id}/projects returns project list (shuffled)', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Projects', testInfo) });
		await attendEvent(authedApi, event.id);
		const created = await createProject(authedApi, {
			name: unique('Covered Project', testInfo),
			description: 'api-coverage test',
			event_id: event.id,
			repo: 'https://github.com/hackclub/podium',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
		});

		const listResp = await getEventProjects(authedApi, event.id, false);
		expect(listResp.ok()).toBe(true);
		const projects = await listResp.json();
		expect(projects.some((p: { id: string }) => p.id === created.id)).toBe(true);

		// leaderboard=true with a VOTING-phase event → 403
		const lbResp = await getEventProjects(authedApi, event.id, true);
		expect(lbResp.status()).toBe(403);
	});

	test('POST /events/{event_id}/attend is idempotent', async ({ authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Attend', testInfo) });
		const first = await attendEvent(authedApi, event.id);
		expect(first.event_id).toBe(event.id);
		const second = await attendEvent(authedApi, event.id);
		expect(second.event_id).toBe(event.id);
	});

	test('POST /events/vote rejects self-votes and records valid votes', async ({
		authedApi
	}, testInfo) => {
		// Organizer (authedApi user) creates event + attends + creates a project
		const event = await createTestEvent(authedApi, { name: unique('Vote', testInfo) });
		await attendEvent(authedApi, event.id);
		const ownProject = await createProject(authedApi, {
			name: unique('Own Project', testInfo),
			description: 'cannot vote for this',
			event_id: event.id,
			repo: 'https://github.com/hackclub/podium',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
		});

		// Attempt to self-vote → 403
		const selfVote = await voteForProjects(authedApi, event.id, [ownProject.id]);
		expect(selfVote.status()).toBe(403);

		// Attendee (separate user) votes for the organizer's project
		const tag = `vote-${Date.now()}-w${testInfo.workerIndex}`;
		const { authedApi: attendeeApi, api: attendeeBase } = await createUserAndGetToken(
			secondaryUserEmail('attendee', tag),
			'Attendee User'
		);
		try {
			await attendEvent(attendeeApi, event.id);
			const ok = await voteForProjects(attendeeApi, event.id, [ownProject.id]);
			expect(ok.ok()).toBe(true);
		} finally {
			await attendeeApi.dispose();
			await attendeeBase.dispose();
		}
	});
});

test.describe('API coverage — PROJECTS router', () => {
	test('GET /projects/mine returns owned + collaborating projects', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Mine', testInfo) });
		await attendEvent(authedApi, event.id);
		const project = await createProject(authedApi, {
			name: unique('Mine Project', testInfo),
			description: '',
			event_id: event.id,
			repo: 'https://github.com/hackclub/podium',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
		});

		const mine = await getMyProjects(authedApi);
		expect(mine.some((p: { id: string }) => p.id === project.id)).toBe(true);
	});

	test('GET /projects/{project_id} returns a public project and 404s on unknown IDs', async ({
		api,
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('GetProj', testInfo) });
		await attendEvent(authedApi, event.id);
		const project = await createProject(authedApi, {
			name: unique('GetProj P', testInfo),
			description: '',
			event_id: event.id,
			repo: 'https://github.com/hackclub/podium',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
		});

		// Public endpoint — anonymous client works
		const resp = await getProject(api, project.id);
		expect(resp.ok()).toBe(true);

		const missing = await getProject(api, BAD_UUID);
		expect(missing.status()).toBe(404);
	});

	test('PUT + DELETE /projects/{id} enforce ownership', async ({ authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Mutate', testInfo) });
		await attendEvent(authedApi, event.id);
		const project = await createProject(authedApi, {
			name: unique('Mutate P', testInfo),
			description: 'orig',
			event_id: event.id,
			repo: 'https://github.com/hackclub/podium',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
		});

		// Update
		const updateResp = await updateProject(authedApi, project.id, {
			description: 'updated by test'
		});
		expect(updateResp.ok()).toBe(true);
		const updated = await updateResp.json();
		expect(updated.description).toBe('updated by test');

		// Non-owner cannot update → 403
		const tag = `owner-${Date.now()}-w${testInfo.workerIndex}`;
		const { authedApi: otherApi, api: otherBase } = await createUserAndGetToken(
			secondaryUserEmail('attendee', tag),
			'Other User'
		);
		try {
			const forbid = await updateProject(otherApi, project.id, { name: 'nope' });
			expect(forbid.status()).toBe(403);

			const forbidDel = await deleteProject(otherApi, project.id);
			expect(forbidDel.status()).toBe(403);
		} finally {
			await otherApi.dispose();
			await otherBase.dispose();
		}

		// Owner can delete
		const delResp = await deleteProject(authedApi, project.id);
		expect(delResp.ok()).toBe(true);
	});

	test('POST /projects/join adds a collaborator via join_code', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Join', testInfo) });
		await attendEvent(authedApi, event.id);
		const project = await createProject(authedApi, {
			name: unique('Join P', testInfo),
			description: '',
			event_id: event.id,
			repo: 'https://github.com/hackclub/podium',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
		});

		const tag = `join-${Date.now()}-w${testInfo.workerIndex}`;
		const { authedApi: collabApi, api: collabBase } = await createUserAndGetToken(
			secondaryUserEmail('attendee', tag),
			'Collab User'
		);
		try {
			await attendEvent(collabApi, event.id);
			const ok = await joinProject(collabApi, project.join_code);
			expect(ok.ok()).toBe(true);

			// Joining twice should be rejected
			const dup = await joinProject(collabApi, project.join_code);
			expect(dup.status()).toBe(400);

			// Unknown code → 404
			const bogus = await joinProject(collabApi, 'NOT-A-REAL-CODE');
			expect(bogus.status()).toBe(404);
		} finally {
			await collabApi.dispose();
			await collabBase.dispose();
		}
	});

	test('POST /projects/validate queues background re-validation', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Validate', testInfo) });
		await attendEvent(authedApi, event.id);

		const project = await createProject(authedApi, {
			name: unique('ToValidate', testInfo),
			description: '',
			event_id: event.id,
			repo: 'https://github.com/hackclub/podium',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
		});

		// Validate queues background work and returns a 200 with valid=true
		const resp = await validateProject(authedApi, project.id);
		expect(resp.ok()).toBe(true);
		const body = await resp.json();
		expect(body).toHaveProperty('valid');
		expect(body).toHaveProperty('message');

		// Non-owner cannot trigger re-validation
		const tag = `valout-${Date.now()}-w${testInfo.workerIndex}`;
		const { authedApi: outsiderApi, api: outsiderBase } = await createUserAndGetToken(
			secondaryUserEmail('attendee', tag),
			'Outsider'
		);
		try {
			const denied = await validateProject(outsiderApi, project.id);
			expect(denied.status()).toBe(403);
		} finally {
			await outsiderApi.dispose();
			await outsiderBase.dispose();
		}
	});
});

test.describe('API coverage — ADMIN router', () => {
	test('GET /events/admin/{id} returns EventPrivate for the owner', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('AdminGet', testInfo) });
		const resp = await adminGetEvent(authedApi, event.id);
		expect(resp.ok()).toBe(true);
		const body = await resp.json();
		expect(body.id).toBe(event.id);
		expect(body).toHaveProperty('owner_id');
	});

	test('GET /events/admin/{id} returns 403 for non-owners', async ({ authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('AdminDeny', testInfo) });
		const tag = `outsider-${Date.now()}-w${testInfo.workerIndex}`;
		const { authedApi: outsiderApi, api: outsiderBase } = await createUserAndGetToken(
			secondaryUserEmail('attendee', tag),
			'Outsider User'
		);
		try {
			const resp = await adminGetEvent(outsiderApi, event.id);
			expect(resp.status()).toBe(403);
		} finally {
			await outsiderApi.dispose();
			await outsiderBase.dispose();
		}
	});

	test('PATCH /events/admin/{id} updates mutable fields', async ({ authedApi }, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('AdminPatch', testInfo) });
		const resp = await adminPatchEvent(authedApi, event.id, {
			description: 'patched by test',
			repo_validation: 'none'
		});
		expect(resp.ok()).toBe(true);
		const body = await resp.json();
		expect(body.description).toBe('patched by test');
		expect(body.repo_validation).toBe('none');
	});

	test('GET /events/admin/{id}/attendees lists attendees', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('AdminAttendees', testInfo) });
		await attendEvent(authedApi, event.id);
		const resp = await adminGetAttendees(authedApi, event.id);
		expect(resp.ok()).toBe(true);
		const attendees = await resp.json();
		expect(Array.isArray(attendees)).toBe(true);
		expect(attendees.length).toBeGreaterThanOrEqual(1);
		expect(attendees[0]).toHaveProperty('email');
	});

	test('POST /events/admin/{id}/remove-attendee drops a user from the event', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('RemoveAtt', testInfo) });
		const tag = `toremove-${Date.now()}-w${testInfo.workerIndex}`;
		const { authedApi: attendeeApi, api: attendeeBase } = await createUserAndGetToken(
			secondaryUserEmail('attendee', tag),
			'To Remove'
		);
		try {
			await attendEvent(attendeeApi, event.id);
			const me = await getCurrentUser(attendeeApi);

			const removeResp = await adminRemoveAttendee(authedApi, event.id, me.id);
			expect(removeResp.ok()).toBe(true);

			const after = await adminGetAttendees(authedApi, event.id);
			const list = await after.json();
			expect(list.some((a: { id: string }) => a.id === me.id)).toBe(false);
		} finally {
			await attendeeApi.dispose();
			await attendeeBase.dispose();
		}
	});

	test('GET /events/admin/{id}/leaderboard returns ranked projects', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('AdminLB', testInfo) });
		await attendEvent(authedApi, event.id);
		await createProject(authedApi, {
			name: unique('LB P', testInfo),
			description: '',
			event_id: event.id,
			repo: 'https://github.com/hackclub/podium',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
		});
		const resp = await adminGetLeaderboard(authedApi, event.id);
		expect(resp.ok()).toBe(true);
		const projects = await resp.json();
		expect(Array.isArray(projects)).toBe(true);
		expect(projects.length).toBeGreaterThanOrEqual(1);
	});

	test('GET /events/admin/{id}/votes lists votes cast on the event', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('AdminVotes', testInfo) });
		await attendEvent(authedApi, event.id);
		const ownerProject = await createProject(authedApi, {
			name: unique('Vote Target', testInfo),
			description: '',
			event_id: event.id,
			repo: 'https://github.com/hackclub/podium',
			image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
		});

		const tag = `voter-${Date.now()}-w${testInfo.workerIndex}`;
		const { authedApi: voterApi, api: voterBase } = await createUserAndGetToken(
			secondaryUserEmail('attendee', tag),
			'Voter User'
		);
		try {
			await attendEvent(voterApi, event.id);
			const voteResp = await voteForProjects(voterApi, event.id, [ownerProject.id]);
			expect(voteResp.ok()).toBe(true);

			const resp = await adminGetVotes(authedApi, event.id);
			expect(resp.ok()).toBe(true);
			const votes = await resp.json();
			expect(votes.length).toBeGreaterThanOrEqual(1);
			expect(votes[0]).toHaveProperty('voter_id');
			expect(votes[0]).toHaveProperty('project_id');
		} finally {
			await voterApi.dispose();
			await voterBase.dispose();
		}
	});

	test('GET /events/admin/{id}/referrals returns the (possibly empty) referral list', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('AdminRef', testInfo) });
		const resp = await adminGetReferrals(authedApi, event.id);
		expect(resp.ok()).toBe(true);
		const referrals = await resp.json();
		expect(Array.isArray(referrals)).toBe(true);
	});
});

test.describe('API coverage — EVENT PHASE lifecycle', () => {
	// Covers the DRAFT → SUBMISSION → VOTING → CLOSED state machine by walking
	// an event through each phase via PATCH and checking that gated endpoints
	// (vote, public leaderboard) flip their access accordingly.
	test('phase transitions gate voting and leaderboard endpoints', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, { name: unique('Lifecycle', testInfo) });
		await attendEvent(authedApi, event.id);

		// Second user will do the voting so we don't hit the self-vote rule.
		const tag = `life-${Date.now()}-w${testInfo.workerIndex}`;
		const { authedApi: voterApi, api: voterBase } = await createUserAndGetToken(
			secondaryUserEmail('attendee', tag),
			'Lifecycle Voter'
		);
		try {
			await attendEvent(voterApi, event.id);
			const project = await createProject(authedApi, {
				name: unique('Lifecycle P', testInfo),
				description: '',
				event_id: event.id,
				repo: 'https://github.com/hackclub/podium',
				image_url: 'https://raw.githubusercontent.com/hackclub/podium/main/README.md'
			});
			// Flip the event to SUBMISSION — voting should now be closed.
			const submissionResp = await adminPatchEvent(authedApi, event.id, { phase: 'submission' });
			expect(submissionResp.ok()).toBe(true);
			const noVote = await voteForProjects(voterApi, event.id, [project.id]);
			expect(noVote.status()).toBe(403);

			// Back to VOTING — vote succeeds.
			const votingResp = await adminPatchEvent(authedApi, event.id, { phase: 'voting' });
			expect(votingResp.ok()).toBe(true);
			const okVote = await voteForProjects(voterApi, event.id, [project.id]);
			expect(okVote.ok()).toBe(true);

			// Public leaderboard is gated on CLOSED phase.
			const hiddenLB = await getEventProjects(voterApi, event.id, true);
			expect(hiddenLB.status()).toBe(403);

			const closedResp = await adminPatchEvent(authedApi, event.id, { phase: 'closed' });
			expect(closedResp.ok()).toBe(true);
			const visibleLB = await getEventProjects(voterApi, event.id, true);
			expect(visibleLB.ok()).toBe(true);
			const lb = await visibleLB.json();
			expect(Array.isArray(lb)).toBe(true);
		} finally {
			await voterApi.dispose();
			await voterBase.dispose();
		}
	});
});

test.describe('API coverage — TEST endpoints', () => {
	test('POST /events/test/create accepts description and sets VOTING phase', async ({
		authedApi
	}, testInfo) => {
		const event = await createTestEvent(authedApi, {
			name: unique('TestCreate', testInfo),
			description: 'with description'
		});
		expect(event.phase).toBe('voting');
		expect(event.description).toBe('with description');
	});

	// POST /events/test/cleanup is intentionally NOT invoked here — it reaps
	// data for every worker and would break parallel tests. It is covered by
	// running it manually out of band or as a post-suite cleanup hook.
});
