# Multi-stage Dockerfile for an optimized Next.js production build
FROM node:20-alpine AS builder
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache python3 make g++ bash

# Copy package metadata and install all dependencies (including dev for build)
COPY package.json package-lock.json* ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build

# Remove dev dependencies to reduce size before copying to final image
RUN npm prune --production || true

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000

# Copy only necessary artifacts from builder
COPY --from= /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

# Use npm start (next start) to run the production server
CMD ["npm", "run", "start"]builder