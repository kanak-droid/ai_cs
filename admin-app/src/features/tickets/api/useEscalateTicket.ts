import { useMutation, useQueryClient } from "@tanstack/react-query";

import { escalateTicket } from "./ticketsApi";
import { ticketsKeys } from "./queryKeys";

export function useEscalateTicket(ticketId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (note: string) => escalateTicket(ticketId, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "tickets", "queue"] });
      queryClient.invalidateQueries({ queryKey: ticketsKeys.detail(ticketId) });
    },
  });
}
