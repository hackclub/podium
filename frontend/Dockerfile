# syntax=docker/dockerfile:1
# Build context: repo root
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@10.20.0 --activate

# ── install all deps (frontend needs devDeps for the build) ───────────────────
FROM base AS deps
WORKDIR /app
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY gateway/package.json ./gateway/
COPY packages/shared/package.json ./packages/shared/
COPY packages/auth-service/package.json ./packages/auth-service/
COPY packages/events-service/package.json ./packages/events-service/
COPY packages/projects-service/package.json ./packages/projects-service/
COPY frontend/package.json ./frontend/
RUN pnpm install --frozen-lockfile --filter podium-frontend...

# ── build ─────────────────────────────────────────────────────────────────────
FROM deps AS builder
WORKDIR /app
COPY frontend/ ./frontend/

# PUBLIC_API_URL is baked in at build time for any static public env references.
# Override via build-arg if your API lives somewhere else.
ARG PUBLIC_API_URL=/api
ENV PUBLIC_API_URL=${PUBLIC_API_URL}

RUN pnpm --filter podium-frontend build

# ── runtime ───────────────────────────────────────────────────────────────────
# adapter-node produces build/index.js — a self-contained HTTP server.
FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app

# Only the built output and its runtime deps are needed.
COPY --from=builder /app/frontend/build ./build
COPY --from=deps    /app/frontend/node_modules ./node_modules
COPY frontend/package.json ./

EXPOSE 3000
CMD ["node", "build/index.js"]
