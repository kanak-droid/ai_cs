import type { Astrologer, CallLogDetail, CallLogSummary } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export interface FeedbackCallFilters {
  dateFrom?: string;
  dateTo?: string;
  astrologer?: string;
}

export function fetchFeedbackCalls(filters: FeedbackCallFilters = {}): Promise<CallLogSummary[]> {
  const params = new URLSearchParams();
  if (filters.dateFrom) params.set("from", filters.dateFrom);
  if (filters.dateTo) params.set("to", filters.dateTo);
  if (filters.astrologer) params.set("astrologer", filters.astrologer);
  const qs = params.toString();
  return api.get<CallLogSummary[]>(`/api/admin/feedback-calls${qs ? `?${qs}` : ""}`);
}

export function fetchFeedbackCallDetail(id: number): Promise<CallLogDetail> {
  return api.get<CallLogDetail>(`/api/admin/feedback-calls/${id}`);
}

export function triggerFeedbackCall(astrologerId: number): Promise<{ call_id: number; status: string }> {
  return api.post("/api/admin/feedback-calls/trigger", { astrologer_id: astrologerId });
}

export function searchAstrologers(query: string): Promise<Astrologer[]> {
  return api.get<Astrologer[]>(`/api/admin/astrologers/search?q=${encodeURIComponent(query)}`);
}
