# Build context MUST be the repo root, not admin-app/ — npm workspaces
# need the root package.json/package-lock.json and packages/shared present
# to install correctly. e.g.:
#   docker build -f admin-app/Dockerfile -t admin-app .
#
# VITE_API_BASE_URL is baked into the static bundle at build time (Vite
# inlines import.meta.env.* during `npm run build`) — pass it as a build
# arg per environment, it can't be changed at container runtime after.
FROM node:20-alpine AS build
WORKDIR /repo

COPY package.json package-lock.json ./
COPY chat-app chat-app
COPY admin-app admin-app
COPY packages packages
RUN npm ci

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build --workspace admin-app

FROM nginx:1.27-alpine
COPY admin-app/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/admin-app/dist /usr/share/nginx/html
EXPOSE 80
