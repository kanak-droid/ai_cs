import { useQuery } from "@tanstack/react-query";
import type { AnalyticsOverview, PriorityFilter } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function useAnalytics(priority?: PriorityFilter) {
  return useQuery({
    queryKey: ["admin", "analytics", priority ?? "all"],
    queryFn: () =>
      api.get<AnalyticsOverview>(
        `/api/admin/analytics${priority ? `?priority=${priority}` : ""}`,
      ),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}
