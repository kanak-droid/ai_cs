import type { AdminAccessLevel } from "@astrohelp/shared";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, type ReactNode } from "react";

import { api } from "../lib/apiClient";
import { authStorage } from "./authStorage";

interface AdminIdentity {
  adminId: number;
  email: string;
  accessLevel: AdminAccessLevel;
}

interface AuthContextValue {
  admin: AdminIdentity | null;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const hasToken = Boolean(authStorage.getToken());

  const { data: admin, isLoading } = useQuery<AdminIdentity | null>({
    queryKey: ["admin", "me"],
    queryFn: async () => {
      const me = await api.get<{ admin_id: number; email: string; access_level: AdminAccessLevel }>(
        "/api/admin/me",
      );
      return { adminId: me.admin_id, email: me.email, accessLevel: me.access_level };
    },
    enabled: hasToken,
    retry: false,
    staleTime: Infinity,
  });

  const login = useCallback(
    async (token: string) => {
      authStorage.setToken(token);
      await queryClient.invalidateQueries({ queryKey: ["admin", "me"] });
    },
    [queryClient],
  );

  const logout = useCallback(() => {
    authStorage.clear();
    queryClient.setQueryData(["admin", "me"], null);
    window.location.assign("/login");
  }, [queryClient]);

  return (
    <AuthContext.Provider
      value={{ admin: admin ?? null, isLoading: hasToken && isLoading, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
