import type { ChatHistoryTurn, ChatResponse } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function sendChatMessage(
  message: string,
  history: ChatHistoryTurn[],
  sessionId: string,
): Promise<ChatResponse> {
  return api.post<ChatResponse>("/api/chat", { message, history, session_id: sessionId });
}
