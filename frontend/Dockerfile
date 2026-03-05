# Build context must be repo root (so frontend/ exists).
# From repo root:  docker build -f frontend/Dockerfile .
# From frontend/:  docker build -f Dockerfile ..
# Staging example:
# docker build -f frontend/Dockerfile \
#   --build-arg NEXT_PUBLIC_API_URL=https://api.staging.klarnow.ai \
#   --build-arg NEXT_PUBLIC_GOOGLE_CLIENT_ID=<staging-google-client-id> \
#   .
FROM node:20-alpine AS base

FROM base AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

FROM base AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_CLIENT_ID}
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
RUN npm run build

FROM base AS runner
WORKDIR /app
# Server-side Next.js route handlers should use deployment runtime BACKEND_URL.
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
