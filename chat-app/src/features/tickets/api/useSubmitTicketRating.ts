import { useMutation, useQueryClient } from "@tanstack/react-query";

import { submitTicketRating } from "./ticketsApi";
import { ticketsKeys } from "./queryKeys";

export function useSubmitTicketRating() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; rating: number; reasons: string[]; comment: string | null }) =>
      submitTicketRating(vars.id, vars.rating, vars.reasons, vars.comment),
    onSuccess: (ticket) => {
      queryClient.setQueryData(ticketsKeys.detail(ticket.id), ticket);
      queryClient.invalidateQueries({ queryKey: ticketsKeys.list() });
    },
  });
}
