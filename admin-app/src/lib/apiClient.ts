import { authStorage } from "../auth/authStorage";
import { ApiError } from "./http-error";

declare global {
  interface Window {
    __RUNTIME_CONFIG__?: { API_BASE_URL?: string };
  }
}

// Prefer the runtime config written by docker-entrypoint.d at container
// startup (see admin-app/Dockerfile) — the build-time VITE_API_BASE_URL is
// frozen into the bundle forever and can't vary per environment. Falls back
// to it anyway for local `npm run dev`, where no config.js is served.
const BASE_URL = window.__RUNTIME_CONFIG__?.API_BASE_URL || import.meta.env.VITE_API_BASE_URL;

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = authStorage.getToken();
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => undefined);
    throw new ApiError(response.status, payload?.detail ?? response.statusText, payload);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
};
