import type { CallLogDetail, CallLogSummary } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export interface CallLogFilters {
  resolutionStatus?: string;
  dateFrom?: string;
  dateTo?: string;
  astrologer?: string;
}

export function fetchCallLogs(filters: CallLogFilters = {}): Promise<CallLogSummary[]> {
  const params = new URLSearchParams();
  if (filters.resolutionStatus) params.set("resolution_status", filters.resolutionStatus);
  if (filters.dateFrom) params.set("from", filters.dateFrom);
  if (filters.dateTo) params.set("to", filters.dateTo);
  if (filters.astrologer) params.set("astrologer", filters.astrologer);
  const qs = params.toString();
  return api.get<CallLogSummary[]>(`/api/admin/call-logs${qs ? `?${qs}` : ""}`);
}

export function fetchCallLogDetail(id: number): Promise<CallLogDetail> {
  return api.get<CallLogDetail>(`/api/admin/call-logs/${id}`);
}
