import type { Ticket } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function fetchTickets(): Promise<Ticket[]> {
  return api.get<Ticket[]>("/api/tickets");
}

export function fetchTicket(id: number): Promise<Ticket> {
  return api.get<Ticket>(`/api/tickets/${id}`);
}

export function submitTicketSatisfaction(id: number, satisfied: boolean): Promise<Ticket> {
  return api.post<Ticket>(`/api/tickets/${id}/satisfaction`, { satisfied });
}
