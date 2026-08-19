import { useQuery } from "@tanstack/react-query";
import type { AnalyticsOverview, PriorityFilter } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function useAnalytics(priority?: PriorityFilter, dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams();
  if (priority) params.set("priority", priority);
  if (dateFrom) params.set("from", dateFrom);
  if (dateTo) params.set("to", dateTo);
  const query = params.toString();

  return useQuery({
    queryKey: ["admin", "analytics", priority ?? "all", dateFrom ?? "", dateTo ?? ""],
    queryFn: () => api.get<AnalyticsOverview>(`/api/admin/analytics${query ? `?${query}` : ""}`),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}
