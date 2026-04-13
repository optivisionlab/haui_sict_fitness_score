# Multi-stage Dockerfile - use pre-built artifacts
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000

# Copy pre-built artifacts from host machine (assuming npm run build was run locally)
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps --production || npm install --production

COPY .env* ./
COPY .next ./.next
COPY public ./public

EXPOSE 3000

# Use npm start (next start) to run the production server
CMD ["npm", "run", "start"]