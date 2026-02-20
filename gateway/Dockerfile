# syntax=docker/dockerfile:1
# Build context: repo root
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@10.20.0 --activate

# ── deps ──────────────────────────────────────────────────────────────────────
FROM base AS deps
WORKDIR /app
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY gateway/package.json ./gateway/
# Stub out every other workspace so pnpm doesn't try to install them
COPY packages/shared/package.json ./packages/shared/
COPY packages/auth-service/package.json ./packages/auth-service/
COPY packages/events-service/package.json ./packages/events-service/
COPY packages/projects-service/package.json ./packages/projects-service/
COPY frontend/package.json ./frontend/
RUN pnpm install --frozen-lockfile --filter podium-gateway...

# ── runtime ───────────────────────────────────────────────────────────────────
FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/gateway/node_modules ./gateway/node_modules
COPY gateway/ ./gateway/

WORKDIR /app/gateway
EXPOSE 3000
CMD ["node", "index.js"]
