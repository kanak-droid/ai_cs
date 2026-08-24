import type { Ticket } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function fetchTickets(): Promise<Ticket[]> {
  return api.get<Ticket[]>("/api/tickets");
}

export function fetchTicket(id: number): Promise<Ticket> {
  return api.get<Ticket>(`/api/tickets/${id}`);
}

export function submitTicketRating(
  id: number,
  rating: number,
  reasons: string[],
  comment: string | null,
): Promise<Ticket> {
  return api.post<Ticket>(`/api/tickets/${id}/rating`, { rating, reasons, comment });
}
