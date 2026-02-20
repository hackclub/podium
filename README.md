# [Podium](https://podium.hackclub.com/)

Peer-judging platform for Hack Club hackathons.

## How It Works

1. **Sign in** — Magic link authentication
2. **Select your event** — Choose from official Hack Club hackathons
3. **Submit your project** — Add name, repo, demo URL
4. **Get validated** — itch.io demos checked for browser playability
5. **Vote** — Browse other projects and vote for your favorites

## For Organizers

Events are pre-created by admins (not users). Use `backend/scripts/manage_events.py` or NocoDB to manage events.

See [docs/architecture.md](docs/architecture.md) for system details.

## Development

```bash
cp .env.example .env

docker compose up -d

./dev.sh
```

See [docs/local-dev.md](docs/local-dev.md) for full setup.
