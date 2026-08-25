import { api } from "../../../lib/apiClient";

export function submitSessionFeedback(
  sessionId: string,
  rating: number,
  reasons: string[],
  comment: string | null,
): Promise<void> {
  return api.post(`/api/chat/sessions/${sessionId}/feedback`, { rating, reasons, comment });
}
