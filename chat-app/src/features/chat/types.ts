import type { ChatTraceStep } from "@astrohelp/shared";

export interface DisplayMessage {
  id: string;
  role: "astrologer" | "assistant";
  text: string;
  // What actually gets resent to the backend as history for this turn — only
  // differs from `text` when it carries an attachment-URL marker the model
  // needs but the astrologer shouldn't see rendered as raw text in the bubble.
  backendText?: string;
  imagePreviewUrl?: string;
  attachmentKind?: "image" | "video";
  trace?: ChatTraceStep[];
  status: "sending" | "sent" | "error";
  showFeedback?: boolean;
  feedbackSubmitted?: boolean;
  // Set when this message is the bot proactively announcing a ticket just
  // got resolved — renders inline Satisfied/Not satisfied buttons for that
  // ticket id. Cleared once the astrologer responds.
  ticketSatisfactionPrompt?: number;
  // Set on the plain ticket-status-change announcements (any transition
  // other than the resolved prompt above) — excludes them from the
  // unrelated "did this solve it?" bot resolve-confirm button, which
  // otherwise attaches to any assistant message that happens to be last.
  isTicketStatusUpdate?: boolean;
}
