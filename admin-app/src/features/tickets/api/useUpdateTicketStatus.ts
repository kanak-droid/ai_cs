import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { TicketStatus } from "@astrohelp/shared";

import { updateTicketStatus } from "./ticketsApi";
import { ticketsKeys } from "./queryKeys";

export function useUpdateTicketStatus(ticketId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ status, note }: { status: TicketStatus; note?: string }) =>
      updateTicketStatus(ticketId, status, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "tickets", "queue"] });
      queryClient.invalidateQueries({ queryKey: ticketsKeys.detail(ticketId) });
    },
  });
}
