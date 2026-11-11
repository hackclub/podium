# Load test

Replays a Haven Saturday against a copy of the production stack: 212 events
with the real per-event roster sizes (`event-sizes.csv`, counts only, taken
from the Haven Airtable base on 2026-11-10), 12,559 participants and 1,151
staff. All users are fake (`*@loadtest.invalid`).

## Where it runs

Orchard project `podium-ui2`, environment `loadtest`
(namespace `ysws-podium-ui2-loadtest-0052f2`), served at
<https://podium-loadtest.k.hackclub.dev>. It mirrors production: same images
built from `feat/ui2`, one replica each, same CPU/memory requests, one Kafka
broker, Redis, and a single-instance CNPG Postgres with default settings.
The app connects to Postgres directly (no PgBouncer), like production.

Nothing in the environment talks to the outside world: SES, Loops, Airtable,
Cockpit and the Haven Airtable token are unset, R2 has dummy values (screenshot
upload will fail), and the GitHub / itch.io checks on submit are turned off
with `k6/settings.js`.

## Running SQL

The loadtest database is not exposed publicly and database pods can't be
exec'd into, so SQL runs from inside the `podium-events` pod, which already has
`pg` and the connection string:

```sh
node loadtest/run-sql.mjs loadtest/check.sql   # prints a command for the pod
```

Run the printed command in the loadtest `podium-events` deployment
(Orchard exec / `orchard exec`).

| File | What it does |
| --- | --- |
| `schema.sql` | `drizzle-kit export` of `packages/shared/src/db/schema.ts` |
| `seed.sql` | Events, users and rosters (`node loadtest/gen-seed.mjs > loadtest/seed.sql`) |
| `reset.sql` | Drops projects and votes, closes voting (Saturday morning) |
| `open-voting.sql` | Closes submissions and opens voting everywhere |
| `reset-votes.sql` | Drops votes only |
| `check.sql` | Integrity checks; every row but the totals must be 0 |

## Running k6

```sh
export JWT_SECRET=...   # the loadtest PODIUM_JWT_SECRET
nix-shell -p k6 --run 'k6 run -e ON=0 loadtest/k6/settings.js'   # GitHub/itch checks off
nix-shell -p k6 --run 'k6 run -e PHASE=checkin -e WINDOW=300 loadtest/k6/podium.js'
```

Tokens are minted locally with the loadtest secret, the same
`{ sub: email, token_type: 'access' }` HS256 token auth-service issues after a
magic link, so no emails are sent.

`PHASE` picks the part of the day; each iteration is one participant's session:

- `checkin`: every present participant opens their event page.
- `submit`: every team owner (odd `j`) submits with teammate `j+1`. One owner
  in ten double-clicks, sending the same submission twice at once.
- `vote`: every present participant loads the vote page and votes for 3
  projects. One in twenty votes from two tabs at once with different picks.
  POCs refresh the admin leaderboard and stats every 10s meanwhile.
  Run `open-voting.sql` first.
- `breakpoint`: read-only vote-page traffic ramped from 10 to 1000 sessions/s,
  aborting when errors pass 1% or project-list p95 passes 500ms.

Other knobs: `WINDOW` (seconds for the crowd to arrive, default 300), `MULT`
(scales the arrival rate), `SHOW` (turnout, default 0.55; `check.sql` assumes
0.55), `EVENT_TZ` and `FORMAT` (narrow to some events, e.g.
`EVENT_TZ=-5 FORMAT=12-hour` for the US-east 12-hour cluster).

A full day is `reset.sql`, `checkin`, `submit`, `open-voting.sql`, `vote`,
then `check.sql`.
