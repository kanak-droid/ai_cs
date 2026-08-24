import { useMutation, useQueryClient } from "@tanstack/react-query";

import { bulkReassignTickets } from "./ticketsApi";

export function useBulkReassignTickets() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      ticketIds,
      role,
      adminId,
      note,
    }: {
      ticketIds: number[];
      role: "kam" | "cs";
      adminId: number;
      note?: string;
    }) => bulkReassignTickets(ticketIds, role, adminId, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "tickets", "queue"] });
    },
  });
}
