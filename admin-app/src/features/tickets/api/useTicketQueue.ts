import { useQuery } from "@tanstack/react-query";

import { fetchTicketQueue } from "./ticketsApi";
import { ticketsKeys, type TicketQueueFilters } from "./queryKeys";

export function useTicketQueue(filters: TicketQueueFilters) {
  return useQuery({
    queryKey: ticketsKeys.queue(filters),
    queryFn: () => fetchTicketQueue(filters),
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });
}
