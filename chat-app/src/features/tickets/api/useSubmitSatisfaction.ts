import { useMutation, useQueryClient } from "@tanstack/react-query";

import { submitTicketSatisfaction } from "./ticketsApi";
import { ticketsKeys } from "./queryKeys";

export function useSubmitSatisfaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; satisfied: boolean }) =>
      submitTicketSatisfaction(vars.id, vars.satisfied),
    onSuccess: (ticket) => {
      queryClient.setQueryData(ticketsKeys.detail(ticket.id), ticket);
      queryClient.invalidateQueries({ queryKey: ticketsKeys.list() });
    },
  });
}
