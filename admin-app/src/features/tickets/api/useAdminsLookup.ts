import { useQuery } from "@tanstack/react-query";
import type { Admin } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

// Powers the "assigned admin" filter dropdown in the ticket queue.
export function useAdminsLookup() {
  return useQuery({
    queryKey: ["admin", "admins"],
    queryFn: () => api.get<Admin[]>("/api/admin/admins"),
    staleTime: 5 * 60_000,
  });
}
