-- Back to Saturday morning: rosters stay, projects and votes go.
BEGIN;
TRUNCATE votes, project_collaborators, projects;
UPDATE events SET votable = false, voting_closed = false, leaderboard_enabled = false WHERE slug LIKE 'lt-%';
COMMIT;
