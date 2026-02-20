# syntax=docker/dockerfile:1
# Build context: repo root
FROM node:22-alpine AS base
ENV CI=true
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@10.20.0 --activate

# ── install all workspace deps needed for the build ───────────────────────────
FROM base AS deps
WORKDIR /app
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY gateway/package.json ./gateway/
COPY packages/shared/package.json ./packages/shared/
COPY packages/auth-service/package.json ./packages/auth-service/
COPY packages/events-service/package.json ./packages/events-service/
COPY packages/projects-service/package.json ./packages/projects-service/
COPY frontend/package.json ./frontend/
RUN pnpm install --frozen-lockfile --filter podium-events-service...

# ── build shared then events-service ──────────────────────────────────────────
FROM deps AS builder
WORKDIR /app
COPY packages/shared/ ./packages/shared/
RUN pnpm --filter @podium/shared build

COPY packages/events-service/ ./packages/events-service/
RUN pnpm --filter podium-events-service build

# ── production deps only ──────────────────────────────────────────────────────
FROM deps AS prod-deps
RUN pnpm install --frozen-lockfile --filter podium-events-service... --prod

# ── runtime ───────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app

COPY --from=builder /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder /app/packages/shared/package.json ./packages/shared/package.json

COPY --from=prod-deps /app/node_modules ./node_modules
COPY --from=prod-deps /app/packages/shared/node_modules ./packages/shared/node_modules
COPY --from=prod-deps /app/packages/events-service/node_modules ./packages/events-service/node_modules
COPY --from=builder  /app/packages/events-service/dist ./packages/events-service/dist
COPY packages/events-service/package.json ./packages/events-service/package.json

WORKDIR /app/packages/events-service
EXPOSE 8002
CMD ["node", "dist/main"]
