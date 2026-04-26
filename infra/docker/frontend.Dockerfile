FROM node:22-alpine AS base

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy package files
COPY apps/frontend/package.json /app/package.json
COPY apps/frontend/pnpm-lock.yaml* /app/

# Install dependencies
RUN pnpm install --frozen-lockfile 2>/dev/null || pnpm install

# Copy source
COPY apps/frontend/ /app/

EXPOSE 3000

# ---- Development target (default for docker compose) ----
FROM base AS dev
ENV NODE_ENV=development
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]

# ---- Production build ----
FROM base AS builder
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# ---- Production runtime ----
FROM node:22-alpine AS prod
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
