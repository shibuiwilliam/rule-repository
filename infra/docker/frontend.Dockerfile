FROM node:22-alpine AS base

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy workspace root files needed for pnpm install
COPY pnpm-workspace.yaml /app/pnpm-workspace.yaml
COPY pnpm-lock.yaml /app/pnpm-lock.yaml
COPY apps/frontend/package.json /app/apps/frontend/package.json

# Install dependencies from workspace root
ENV COREPACK_ENABLE_STRICT=0
RUN pnpm install --frozen-lockfile --filter rulerepo-frontend --ignore-scripts

# Copy frontend source into the workspace member location
COPY apps/frontend/ /app/apps/frontend/

WORKDIR /app/apps/frontend

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

COPY --from=builder /app/apps/frontend/.next/standalone ./
COPY --from=builder /app/apps/frontend/.next/static ./.next/static
COPY --from=builder /app/apps/frontend/public ./public 2>/dev/null || true

EXPOSE 3000
CMD ["node", "server.js"]
