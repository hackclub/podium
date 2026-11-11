-- Integrity checks after a load test run. Every row except the *_total and
-- *_info rows must be 0. Assumes SHOW = 0.55, the k6 default.
WITH roster AS (
  SELECT u.id AS user_id, e.id AS event_id,
         split_part(split_part(u.email, '@', 1), '-', 3)::int AS j,
         count(*) OVER (PARTITION BY e.id) AS p
  FROM users u
  JOIN events e ON e.slug = 'lt-' || split_part(split_part(u.email, '@', 1), '-', 2)
  WHERE u.email LIKE 'p-%@loadtest.invalid'
),
present AS (
  SELECT user_id, event_id FROM roster WHERE j <= ceil(p * 0.55)
),
eligible AS (
  SELECT pr.user_id, pr.event_id, count(pj.id) AS n
  FROM present pr
  JOIN projects pj ON pj.event_id = pr.event_id
  WHERE pj.owner_id <> pr.user_id
    AND NOT EXISTS (SELECT 1 FROM project_collaborators c WHERE c.project_id = pj.id AND c.user_id = pr.user_id)
  GROUP BY 1, 2
),
cast_votes AS (
  SELECT voter_id, event_id, count(*) AS n FROM votes GROUP BY 1, 2
)
SELECT 'owners_with_2+_projects' AS name, count(*) AS n
FROM (SELECT 1 FROM projects GROUP BY owner_id, event_id HAVING count(*) > 1) x
UNION ALL
SELECT 'projects_missing_teammate', count(*)
FROM projects pj
JOIN users o ON o.id = pj.owner_id
JOIN roster r ON r.user_id = o.id
WHERE r.j + 1 <= ceil(r.p * 0.55)
  AND NOT EXISTS (SELECT 1 FROM project_collaborators c WHERE c.project_id = pj.id)
UNION ALL
SELECT 'voters_over_3', count(*) FROM cast_votes WHERE n > 3
UNION ALL
SELECT 'votes_for_own_project', count(*) FROM votes v JOIN projects pj ON pj.id = v.project_id WHERE pj.owner_id = v.voter_id
UNION ALL
SELECT 'votes_for_collab_project', count(*)
FROM votes v JOIN project_collaborators c ON c.project_id = v.project_id AND c.user_id = v.voter_id
UNION ALL
SELECT 'votes_wrong_event', count(*) FROM votes v JOIN projects pj ON pj.id = v.project_id WHERE pj.event_id <> v.event_id
UNION ALL
-- Lost votes: a present participant at an event that voted ended up with
-- fewer than min(3, projects they could vote for).
SELECT 'voters_short_of_ballot', count(*)
FROM eligible el
LEFT JOIN cast_votes cv ON cv.voter_id = el.user_id AND cv.event_id = el.event_id
WHERE el.event_id IN (SELECT DISTINCT event_id FROM votes)
  AND coalesce(cv.n, 0) < least(3, el.n)
UNION ALL
SELECT 'projects_total', count(*) FROM projects
UNION ALL
SELECT 'votes_total', count(*) FROM votes
UNION ALL
SELECT 'events_with_votes_info', count(DISTINCT event_id) FROM votes;
