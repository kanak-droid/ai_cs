import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { api, setAuthToken } from "../lib/apiClient";
import { ApiError } from "../lib/http-error";

export interface AstrologerIdentity {
  astrologerId: number;
  name: string;
  language: string;
}

interface VerifyResponse {
  astrologer_id: number;
  name: string;
  language: string;
}

export function useAstrologerSession() {
  // Read once on mount — the WebView host always includes this on a fresh
  // load, which is the only time this needs to be re-read (a client-side
  // <Link> navigation never drops it, since identity is already in memory).
  //
  // This is a plain user_id, not a signed token — the main AstroLokal app's
  // banner hand-off carries no signature at all (confirmed 2026-08-14), so
  // there is nothing to verify here beyond "does a real astrologer have this
  // user_id" (done server-side in /api/auth/verify).
  const userId = useMemo(() => new URLSearchParams(window.location.search).get("user_id"), []);

  return useQuery<AstrologerIdentity>({
    queryKey: ["auth", "verify", userId],
    queryFn: async () => {
      if (!userId) {
        throw new ApiError(401, "No user_id was provided.");
      }
      setAuthToken(userId);
      const verified = await api.get<VerifyResponse>("/api/auth/verify");
      return {
        astrologerId: verified.astrologer_id,
        name: verified.name,
        language: verified.language,
      };
    },
    retry: false,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
}
