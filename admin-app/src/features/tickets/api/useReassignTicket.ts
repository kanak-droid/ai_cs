import { useMutation, useQueryClient } from "@tanstack/react-query";

import { reassignTicket } from "./ticketsApi";
import { ticketsKeys } from "./queryKeys";

export function useReassignTicket(ticketId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ role, adminId, note }: { role: "kam" | "cs"; adminId: number; note?: string }) =>
      reassignTicket(ticketId, role, adminId, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "tickets", "queue"] });
      queryClient.invalidateQueries({ queryKey: ticketsKeys.detail(ticketId) });
    },
  });
}
