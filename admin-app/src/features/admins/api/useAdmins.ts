import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { Admin, AdminAccessLevel, AdminRole } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

const adminsKey = ["admin", "admins", "all"] as const;

export function useAllAdmins() {
  return useQuery({
    queryKey: adminsKey,
    queryFn: () => api.get<Admin[]>("/api/admin/admins?include_inactive=true"),
  });
}

export function useCreateAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      email: string;
      role: AdminRole;
      access_level: AdminAccessLevel;
      languages: string[];
    }) => api.post<Admin>("/api/admin/admins", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminsKey }),
  });
}

export function useUpdateAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: {
      id: number;
      role?: AdminRole;
      access_level?: AdminAccessLevel;
      languages?: string[];
      is_active?: boolean;
    }) => api.patch<Admin>(`/api/admin/admins/${id}`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: adminsKey }),
  });
}
