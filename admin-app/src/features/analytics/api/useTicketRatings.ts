import { useQuery } from "@tanstack/react-query";
import type { PriorityFilter, TicketRatingEntry } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

// Only fetched once the admin actually opens the ratings panel (see
// TicketRatingsModal) — `enabled` gates it so a page load never pulls every
// individual rating just because the stat card is on screen.
export function useTicketRatings(
  enabled: boolean,
  priority?: PriorityFilter,
  dateFrom?: string,
  dateTo?: string,
) {
  const params = new URLSearchParams();
  if (priority) params.set("priority", priority);
  if (dateFrom) params.set("from", dateFrom);
  if (dateTo) params.set("to", dateTo);
  const query = params.toString();

  return useQuery({
    queryKey: ["admin", "analytics", "ticket-ratings", priority ?? "all", dateFrom ?? "", dateTo ?? ""],
    queryFn: () =>
      api.get<TicketRatingEntry[]>(`/api/admin/analytics/ticket-ratings${query ? `?${query}` : ""}`),
    enabled,
  });
}
