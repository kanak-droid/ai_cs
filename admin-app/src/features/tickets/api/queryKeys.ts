export interface TicketQueueFilters {
  status?: string;
  assignedAdminId?: number;
  sort: "asc" | "desc" | "priority";
  // ISO dates ("YYYY-MM-DD") filtering on Ticket.created_at — either can be
  // set alone for an open-ended range; equal values mean "just this day".
  dateFrom?: string;
  dateTo?: string;
}

export const ticketsKeys = {
  queue: (filters: TicketQueueFilters) => ["admin", "tickets", "queue", filters] as const,
  detail: (id: number) => ["admin", "tickets", "detail", id] as const,
};
