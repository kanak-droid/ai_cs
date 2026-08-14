import { useQuery } from "@tanstack/react-query";

import { fetchTicket } from "./ticketsApi";
import { ticketsKeys } from "./queryKeys";

export function useTicket(id: number) {
  return useQuery({
    queryKey: ticketsKeys.detail(id),
    queryFn: () => fetchTicket(id),
    // Keep polling through "resolved" — that's exactly when the astrologer
    // still needs to respond satisfied/unsatisfied; only "closed" is final.
    refetchInterval: (query) => (query.state.data?.status === "closed" ? false : 15_000),
    refetchIntervalInBackground: false,
  });
}
