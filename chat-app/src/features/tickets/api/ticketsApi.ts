import type { Ticket } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function fetchTickets(): Promise<Ticket[]> {
  return api.get<Ticket[]>("/api/tickets");
}

export function fetchTicket(id: number): Promise<Ticket> {
  return api.get<Ticket>(`/api/tickets/${id}`);
}
