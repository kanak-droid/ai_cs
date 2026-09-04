import type { Astrologer, CallLogSummary, ChatSessionSummary, Ticket } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function fetchAstrologers(): Promise<Astrologer[]> {
  return api.get<Astrologer[]>("/api/admin/astrologers");
}

export interface AstrologerOverview {
  astrologer: Astrologer;
  tickets: Ticket[];
  calls: CallLogSummary[];
  chat_sessions: ChatSessionSummary[];
}

export function searchAstrologers(query: string): Promise<Astrologer[]> {
  return api.get<Astrologer[]>(`/api/admin/astrologers/search?q=${encodeURIComponent(query)}`);
}

export function fetchAstrologerOverview(id: number): Promise<AstrologerOverview> {
  return api.get<AstrologerOverview>(`/api/admin/astrologers/${id}/overview`);
}
