import { useQuery } from "@tanstack/react-query";
import type { EmailLogEntry } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function useEmailLog() {
  return useQuery({
    queryKey: ["admin", "email-log"],
    queryFn: () => api.get<EmailLogEntry[]>("/api/admin/email-log"),
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });
}
