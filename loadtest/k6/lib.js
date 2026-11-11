// Shared helpers for the k6 scenarios. See loadtest/README.md.
import http from 'k6/http';
import { check } from 'k6';
import { hmac } from 'k6/crypto';
import encoding from 'k6/encoding';

export const BASE = __ENV.BASE_URL || 'https://podium-loadtest.k.hackclub.dev';
// Fraction of each roster that shows up. check.sql assumes the same value.
export const SHOW = Number(__ENV.SHOW || 0.55);
const SECRET = __ENV.JWT_SECRET;
if (!SECRET) throw new Error('JWT_SECRET is required (the loadtest PODIUM_JWT_SECRET)');

// tz_offset,format,participants,staff, one row per event; row i is event lt-<i>.
export const EVENTS = open('../event-sizes.csv')
  .trim()
  .split('\n')
  .slice(1)
  .map((line, i) => {
    const [tz, format, participants, staff] = line.split(',');
    const p = Number(participants);
    return { idx: i + 1, slug: `lt-${i + 1}`, tz: Number(tz), format, p, s: Number(staff), present: Math.ceil(p * SHOW) };
  });

/** Events matching the EVENT_TZ / FORMAT env filters (e.g. EVENT_TZ=-5 FORMAT=12-hour for the US-east cluster). */
export function selectedEvents() {
  return EVENTS.filter(
    (e) =>
      (__ENV.EVENT_TZ === undefined || e.tz === Number(__ENV.EVENT_TZ)) &&
      (__ENV.FORMAT === undefined || e.format === __ENV.FORMAT),
  );
}

/** Every participant who shows up at the given events, as { event, j, email }. */
export function presentParticipants(events) {
  const out = [];
  for (const event of events) {
    for (let j = 1; j <= event.present; j++) {
      out.push({ event, j, email: participantEmail(event.idx, j) });
    }
  }
  return out;
}

export const participantEmail = (idx, j) => `p-${idx}-${j}@loadtest.invalid`;
export const staffEmail = (idx, j) => `s-${idx}-${j}@loadtest.invalid`;
export const ADMIN_EMAIL = 'admin@loadtest.invalid';

const b64url = (s) => encoding.b64encode(s, 'rawurl');

/** Same token auth-service issues after a magic link: HS256 { sub: email, token_type: 'access' }. */
export function token(email) {
  const now = Math.floor(Date.now() / 1000);
  const head = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = b64url(JSON.stringify({ sub: email, token_type: 'access', iat: now, exp: now + 6 * 3600 }));
  const sig = hmac('sha256', SECRET, `${head}.${body}`, 'base64rawurl');
  return `${head}.${body}.${sig}`;
}

export function authed(email, name) {
  return {
    headers: { Authorization: `Bearer ${token(email)}`, 'Content-Type': 'application/json' },
    tags: { name },
  };
}

export function api(method, path, email, name, body) {
  const params = email ? authed(email, name) : { tags: { name }, headers: { 'Content-Type': 'application/json' } };
  return http.request(method, `${BASE}/api${path}`, body === undefined ? null : JSON.stringify(body), params);
}

const eventIds = {};
/** Resolves an event slug the way the frontend layout does (GET /events/id/:slug). Cached per VU. */
export function eventId(event, email) {
  if (!eventIds[event.slug]) {
    const res = api('GET', `/events/id/${event.slug}`, email, 'GET /events/id/:slug');
    check(res, { 'slug resolved': (r) => r.status === 200 });
    eventIds[event.slug] = res.status === 200 ? res.json('id') : null;
  }
  return eventIds[event.slug];
}

/** The requests a participant's browser makes when opening an event page. */
export function openEventPage(event, email) {
  http.get(`${BASE}/${event.slug}`, { tags: { name: 'GET /:slug (html)' } });
  const id = eventId(event, email);
  if (!id) return null;
  const [ev, me] = http.batch([
    ['GET', `${BASE}/api/events/${id}`, null, authed(email, 'GET /events/:id')],
    ['GET', `${BASE}/api/users/current`, null, authed(email, 'GET /users/current')],
    ['GET', `${BASE}/api/projects/mine`, null, authed(email, 'GET /projects/mine')],
  ]);
  check(ev, { 'event 200': (r) => r.status === 200 });
  check(me, { 'current user 200': (r) => r.status === 200 });
  return { id, me: me.status === 200 ? me.json() : null };
}

/** Deterministic pseudo-random pick so reruns hit the same users the same way. */
export function pick(arr, n, seed) {
  const copy = arr.slice();
  let s = seed;
  for (let i = copy.length - 1; i > 0; i--) {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    const k = s % (i + 1);
    [copy[i], copy[k]] = [copy[k], copy[i]];
  }
  return copy.slice(0, n);
}
