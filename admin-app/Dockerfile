# Build context MUST be the repo root, not admin-app/ — npm workspaces
# need the root package.json/package-lock.json and packages/shared present
# to install correctly. e.g.:
#   docker build -f admin-app/Dockerfile -t admin-app .
#
# VITE_API_BASE_URL used to be the only way to point this app at a backend,
# but Vite bakes import.meta.env.* into the static bundle at build time — it
# can never change at container runtime after, so the same built image
# couldn't be deployed to more than one environment (dev vs. production)
# without a full rebuild each time. Confirmed live 2026-08-18: production's
# admin dashboard was silently calling the dev backend because this ARG's
# default was never overridden for the production build, and this Devtron
# instance's Build Configuration UI has no exposed field for passing
# --build-arg through to the CI pipeline anyway.
#
# The real, per-environment URL now comes from docker-entrypoint.d's
# generate-runtime-config script, sourced from a normal container env var
# (API_BASE_URL) at container *startup*, not build time — see
# admin-app/src/lib/apiClient.ts for how it's consumed. This ARG only
# remains as the fallback `npm run dev` / non-Docker build value.
FROM node:20-alpine AS build
WORKDIR /repo

COPY package.json package-lock.json ./
COPY chat-app chat-app
COPY admin-app admin-app
COPY packages packages
RUN npm ci

ARG VITE_API_BASE_URL=https://dev-astro-supply-help-chat.astrolokal.com
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build --workspace admin-app

FROM nginx:1.27-alpine
COPY admin-app/nginx.conf /etc/nginx/conf.d/default.conf
COPY admin-app/docker-entrypoint.d/40-generate-runtime-config.sh /docker-entrypoint.d/40-generate-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-generate-runtime-config.sh
COPY --from=build /repo/admin-app/dist /usr/share/nginx/html
EXPOSE 80
