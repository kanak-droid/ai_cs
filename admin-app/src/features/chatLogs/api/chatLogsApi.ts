import type { ChatSessionDetail, ChatSessionSummary } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function fetchChatSessions(): Promise<ChatSessionSummary[]> {
  return api.get<ChatSessionSummary[]>("/api/admin/chat-sessions");
}

export function fetchChatSessionDetail(id: number): Promise<ChatSessionDetail> {
  return api.get<ChatSessionDetail>(`/api/admin/chat-sessions/${id}`);
}
