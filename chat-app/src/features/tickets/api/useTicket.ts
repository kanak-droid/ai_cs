import { useQuery } from "@tanstack/react-query";

import { fetchTicket } from "./ticketsApi";
import { ticketsKeys } from "./queryKeys";

export function useTicket(id: number) {
  return useQuery({
    queryKey: ticketsKeys.detail(id),
    queryFn: () => fetchTicket(id),
    refetchInterval: (query) => (query.state.data?.status === "resolved" ? false : 15_000),
    refetchIntervalInBackground: false,
  });
}
