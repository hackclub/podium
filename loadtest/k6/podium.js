// Saturday, replayed. Each iteration is one participant's session, drawn from
// the seeded rosters (see lib.js). Pick the phase with PHASE:
//
//   checkin     everyone at the selected events opens their event page
//   submit      every team owner submits (with a teammate); some double-click
//   vote        everyone votes 3 times; some vote from two tabs at once;
//               POCs refresh the leaderboard while it happens
//   breakpoint  vote-page reads ramped until latency or errors give out
//
// WINDOW (seconds) is how long the selected crowd takes to arrive. MULT scales
// the arrival rate. EVENT_TZ / FORMAT narrow the events (default: all 212).
import http from 'k6/http';
import exec from 'k6/execution';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';
import {
  BASE, api, authed, eventId, openEventPage, pick, presentParticipants, selectedEvents, staffEmail,
} from './lib.js';

const PHASE = __ENV.PHASE || 'checkin';
const WINDOW = Number(__ENV.WINDOW || 300);
const MULT = Number(__ENV.MULT || 1);

const events = selectedEvents();
const people = presentParticipants(events);
// Teams of two: odd j owns the project, j+1 is the teammate.
const owners = people.filter((u) => u.j % 2 === 1);

const votesAccepted = new Counter('votes_accepted');
const votesRejected = new Counter('votes_rejected');
const projectsCreated = new Counter('projects_created');
const projectsRejected = new Counter('projects_rejected');

const population = { checkin: people, submit: owners, vote: people, breakpoint: people }[PHASE];
if (!population) throw new Error(`unknown PHASE ${PHASE}`);

function arrivals(count) {
  return {
    executor: 'constant-arrival-rate',
    rate: Math.max(1, Math.ceil((count / WINDOW) * MULT)),
    timeUnit: '1s',
    duration: `${WINDOW}s`,
    preAllocatedVUs: 200,
    maxVUs: 3000,
  };
}

const scenarios = {};
if (PHASE === 'breakpoint') {
  scenarios.breakpoint = {
    executor: 'ramping-arrival-rate',
    startRate: 10,
    timeUnit: '1s',
    preAllocatedVUs: 300,
    maxVUs: 5000,
    stages: [
      { target: 50, duration: '1m' },
      { target: 150, duration: '2m' },
      { target: 300, duration: '2m' },
      { target: 600, duration: '2m' },
      { target: 1000, duration: '2m' },
    ],
    exec: 'browse',
  };
} else {
  scenarios[PHASE] = { ...arrivals(population.length), exec: PHASE };
  if (PHASE === 'vote') {
    scenarios.organizers = {
      executor: 'constant-vus',
      vus: Math.min(events.length, 100),
      duration: `${WINDOW}s`,
      exec: 'organizer',
    };
  }
}

export const options = {
  scenarios,
  thresholds: {
    http_req_failed: [{ threshold: 'rate<0.01', abortOnFail: PHASE === 'breakpoint', delayAbortEval: '30s' }],
    'http_req_duration{name:GET /events/:id/projects}': [{ threshold: 'p(95)<500', abortOnFail: PHASE === 'breakpoint', delayAbortEval: '30s' }],
    'http_req_duration{name:POST /events/vote}': ['p(95)<1000'],
    'http_req_duration{name:POST /projects}': ['p(95)<1000'],
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(95)', 'p(99)', 'max'],
};

// Always-passing thresholds so the summary breaks latency down per endpoint.
for (const name of [
  'GET /:slug (html)', 'GET /events/id/:slug', 'GET /events/:id', 'GET /users/current', 'GET /projects/mine',
  'GET /events/:id/my-votes', 'GET /events/admin/:id/leaderboard', 'GET /events/admin/:id/stats',
]) {
  options.thresholds[`http_req_duration{name:${name}}`] = ['max>=0'];
}

export function setup() {
  console.log(`${PHASE}: ${events.length} events, ${people.length} present participants, ${population.length} sessions over ${WINDOW}s (x${MULT})`);
}

/** The person this iteration plays, or null once everyone has had their turn. */
function me() {
  const i = exec.scenario.iterationInTest;
  return i < population.length ? population[i] : null;
}

export function checkin() {
  const u = me();
  if (!u) return;
  openEventPage(u.event, u.email);
}

export function submit() {
  const u = me();
  if (!u) return;
  const page = openEventPage(u.event, u.email);
  if (!page) return;
  const teammate = u.j + 1 <= u.event.present ? `p-${u.event.idx}-${u.j + 1}@loadtest.invalid` : null;
  const body = JSON.stringify({
    name: `Game ${u.event.idx}-${u.j}`,
    repo: `https://github.com/loadtest-${u.event.idx}/game-${u.j}`,
    image_url: 'https://loadtest.invalid/screenshot.png',
    demo: `https://loadtest-${u.event.idx}.itch.io/game-${u.j}`,
    description: 'A load test game.',
    hours_spent: 10,
    event_id: page.id,
    teammates: teammate ? [{ email: teammate }] : [],
  });
  const req = ['POST', `${BASE}/api/projects`, body, authed(u.email, 'POST /projects')];
  // 1 in 10 owners double-clicks Submit: both requests race, exactly one project may survive.
  const doubleClick = u.j % 20 === 1;
  const responses = doubleClick ? http.batch([req, req]) : [http.request(...req)];
  for (const res of responses) {
    if (res.status === 201 || res.status === 200) projectsCreated.add(1);
    else projectsRejected.add(1, { status: String(res.status) });
  }
  check(responses[0], { 'project submitted': (r) => r.status === 201 || r.status === 200 || (doubleClick && r.status === 409) });
  if (teammate) api('GET', '/projects/mine', teammate, 'GET /projects/mine');
}

/** Opens the vote page and returns the projects this user may vote for. */
function votePage(u) {
  const page = openEventPage(u.event, u.email);
  if (!page || !page.me) return null;
  const [list] = http.batch([
    ['GET', `${BASE}/api/events/${page.id}/projects`, null, authed(u.email, 'GET /events/:id/projects')],
    ['GET', `${BASE}/api/events/${page.id}/my-votes`, null, authed(u.email, 'GET /events/:id/my-votes')],
  ]);
  check(list, { 'projects 200': (r) => r.status === 200 });
  if (list.status !== 200) return null;
  const mine = (p) => p.owner_id === page.me.id || p.collaborators.some((c) => c.user_id === page.me.id);
  return { id: page.id, eligible: list.json().filter((p) => !mine(p)).map((p) => p.id) };
}

function castVote(email, eventUuid, projectIds) {
  return ['POST', `${BASE}/api/events/vote`, JSON.stringify({ event: eventUuid, projects: projectIds }), authed(email, 'POST /events/vote')];
}

export function vote() {
  const u = me();
  if (!u) return;
  const page = votePage(u);
  if (!page || page.eligible.length === 0) return;
  sleep(Math.random() * 20); // looking at the projects
  const ballot = pick(page.eligible, 3, u.event.idx * 1000 + u.j);
  // 1 in 20 votes from two tabs at once with different picks: the 3-vote cap must still hold.
  const twoTabs = u.j % 20 === 0 && page.eligible.length > 3;
  const reqs = [castVote(u.email, page.id, ballot)];
  if (twoTabs) reqs.push(castVote(u.email, page.id, pick(page.eligible, 3, u.event.idx * 7919 + u.j)));
  for (const res of http.batch(reqs)) {
    if (res.status === 202) votesAccepted.add(1);
    else votesRejected.add(1, { status: String(res.status) });
    check(res, { 'vote accepted': (r) => r.status === 202 });
  }
}

/** A POC with the admin leaderboard open, refreshing it. */
export function organizer() {
  const event = events[(exec.vu.idInTest - 1) % events.length];
  const email = staffEmail(event.idx, 1);
  if (event.s < 1) return sleep(10);
  const id = eventId(event, email);
  if (!id) return sleep(10);
  http.batch([
    ['GET', `${BASE}/api/events/admin/${id}/leaderboard`, null, authed(email, 'GET /events/admin/:id/leaderboard')],
    ['GET', `${BASE}/api/events/admin/${id}/stats`, null, authed(email, 'GET /events/admin/:id/stats')],
  ]);
  sleep(10);
}

/** Read-only vote-page traffic for the breakpoint ramp (repeatable, writes nothing). */
export function browse() {
  const u = people[exec.scenario.iterationInTest % people.length];
  votePage(u);
}
