-- Submissions close, voting opens, at every loadtest event.
UPDATE events SET votable = true, voting_closed = false, leaderboard_enabled = true WHERE slug LIKE 'lt-%';
