import { useQuery } from "@tanstack/react-query";
import type { SlackLogEntry } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function useSlackLog() {
  return useQuery({
    queryKey: ["admin", "slack-log"],
    queryFn: () => api.get<SlackLogEntry[]>("/api/admin/slack-log"),
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });
}
