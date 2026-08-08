import type { ChatTraceStep } from "@astrohelp/shared";

export interface DisplayMessage {
  id: string;
  role: "astrologer" | "assistant";
  text: string;
  imagePreviewUrl?: string;
  trace?: ChatTraceStep[];
  status: "sending" | "sent" | "error";
}
