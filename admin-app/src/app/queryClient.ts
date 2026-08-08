import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { authStorage } from "../auth/authStorage";
import { ApiError } from "../lib/http-error";

// Single choke point for "the admin's session expired" — no per-hook 401
// checks scattered across every query/mutation.
function handleAuthError(error: unknown): void {
  if (error instanceof ApiError && error.status === 401) {
    authStorage.clear();
    if (window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
  }
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 10_000,
    },
    mutations: {
      retry: false,
    },
  },
  queryCache: new QueryCache({ onError: handleAuthError }),
  mutationCache: new MutationCache({ onError: handleAuthError }),
});
