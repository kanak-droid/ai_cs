export interface TicketQueueFilters {
  status?: string;
  assignedAdminId?: number;
  sort: "asc" | "desc" | "priority";
}

export const ticketsKeys = {
  queue: (filters: TicketQueueFilters) => ["admin", "tickets", "queue", filters] as const,
  detail: (id: number) => ["admin", "tickets", "detail", id] as const,
};
