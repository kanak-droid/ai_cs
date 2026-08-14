import { useQuery } from "@tanstack/react-query";
import type { AnalyticsOverview } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function useAnalytics() {
  return useQuery({
    queryKey: ["admin", "analytics"],
    queryFn: () => api.get<AnalyticsOverview>("/api/admin/analytics"),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}
