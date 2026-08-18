export interface ChatLogMessage {
  role: string;
  text: string;
  created_at: string;
}

export interface ChatSessionSummary {
  id: number;
  session_id: string;
  astrologer_id: number;
  astrologer_name: string;
  priority: number | null;
  category: string | null;
  sub_category: string | null;
  // "bot" | "escalated" | null (still an open, unconcluded conversation)
  resolved_by: string | null;
  ticket_id: number | null;
  started_at: string;
  resolved_at: string | null;
}

export interface ChatSessionDetail extends ChatSessionSummary {
  // Empty for sessions that started before message persistence shipped
  // (2026-08-18) — only ChatSession's own resolution metadata exists for those.
  messages: ChatLogMessage[];
}
