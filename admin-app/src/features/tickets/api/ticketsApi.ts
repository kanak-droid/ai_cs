import type { AdminTicket, TicketStatus } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";
import type { TicketQueueFilters } from "./queryKeys";

function toSearchParams(filters: TicketQueueFilters): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.assignedAdminId) params.set("assigned_admin_id", String(filters.assignedAdminId));
  params.set("sort", filters.sort);
  return params.toString();
}

export function fetchTicketQueue(filters: TicketQueueFilters): Promise<AdminTicket[]> {
  return api.get<AdminTicket[]>(`/api/admin/tickets?${toSearchParams(filters)}`);
}

export function fetchTicketDetail(id: number): Promise<AdminTicket> {
  return api.get<AdminTicket>(`/api/admin/tickets/${id}`);
}

export function updateTicketStatus(
  id: number,
  status: TicketStatus,
  note?: string,
): Promise<AdminTicket> {
  return api.patch<AdminTicket>(`/api/admin/tickets/${id}`, { status, note });
}
