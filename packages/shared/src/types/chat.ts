export interface ChatTraceStep {
  tool: string;
  ok: boolean;
  summary: string;
}

export interface ChatHistoryTurn {
  role: "astrologer" | "assistant";
  text: string;
}

export interface ChatRequest {
  message: string;
  // Prior turns of this conversation — the backend is stateless across
  // requests, so without this the model has no memory of anything said
  // earlier in the chat.
  history: ChatHistoryTurn[];
}

export interface ChatResponse {
  reply: string;
  trace: ChatTraceStep[];
}
