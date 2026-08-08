import type { ChatResponse } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function sendChatMessage(message: string): Promise<ChatResponse> {
  return api.post<ChatResponse>("/api/chat", { message });
}
