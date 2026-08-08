import { useQuery } from "@tanstack/react-query";

import { fetchTickets } from "./ticketsApi";
import { ticketsKeys } from "./queryKeys";

export function useTickets() {
  return useQuery({
    queryKey: ticketsKeys.list(),
    queryFn: fetchTickets,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });
}
