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
  const token = useMemo(() => new URLSearchParams(window.location.search).get("token"), []);

  return useQuery<AstrologerIdentity>({
    queryKey: ["auth", "verify", token],
    queryFn: async () => {
      if (!token) {
        throw new ApiError(401, "No session token was provided.");
      }
      setAuthToken(token);
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
