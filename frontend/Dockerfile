# Build from repo root (e.g. Railway):  docker build -f frontend/Dockerfile .
# Build from frontend/:  docker build -f Dockerfile . --build-arg SRC=.
FROM node:20-alpine AS base

FROM base AS deps
ARG SRC=frontend
WORKDIR /app
COPY ${SRC}/package.json ${SRC}/package-lock.json* ./
RUN npm ci

FROM base AS builder
WORKDIR /app
ARG SRC=frontend
COPY --from=deps /app/node_modules ./node_modules
COPY ${SRC}/ .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}
RUN npm run build

FROM base AS runner
WORKDIR /app
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
