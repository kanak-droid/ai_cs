import { useQuery } from "@tanstack/react-query";

import { fetchTicketDetail } from "./ticketsApi";
import { ticketsKeys } from "./queryKeys";

export function useTicketDetail(id: number) {
  return useQuery({
    queryKey: ticketsKeys.detail(id),
    queryFn: () => fetchTicketDetail(id),
    refetchInterval: (query) => (query.state.data?.status === "resolved" ? false : 20_000),
    refetchIntervalInBackground: false,
  });
}
