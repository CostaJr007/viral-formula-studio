# Viral Formula Studio — React frontend (TanStack Start)
FROM node:22-slim AS build

WORKDIR /app
COPY package.json package-lock.json ./
# Prefer clean install; fall back if lock drifts (avoids failed web deploys)
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

COPY . .
# VITE_API_URL is inlined at build time (points to the API service URL)
ARG VITE_API_URL=https://vfs-api.2cfhg08pznl4.us-south.codeengine.appdomain.cloud
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM node:22-slim
WORKDIR /app
COPY --from=build /app ./

ENV NODE_ENV=production
EXPOSE 4173
CMD ["sh", "-c", "npm run preview -- --host 0.0.0.0 --port ${PORT:-4173}"]
