#!/bin/sh
# Vite bakes VITE_API_BASE_URL into the JS bundle at build time (see
# admin-app/Dockerfile) — it can never change after that, which meant the
# same image couldn't be deployed to more than one environment without
# rebaking. This writes a small runtime-read config file instead, sourced
# from a normal container env var (API_BASE_URL, set per-environment same
# as any other Devtron env var) — see admin-app/src/lib/apiClient.ts for how
# it's consumed. Dropped in /docker-entrypoint.d/, the official nginx image's
# own entrypoint runs every executable script here before starting nginx.
set -e

cat > /usr/share/nginx/html/config.js <<EOF
window.__RUNTIME_CONFIG__ = { API_BASE_URL: "${API_BASE_URL:-}" };
EOF
