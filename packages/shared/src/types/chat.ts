export interface ChatTraceStep {
  tool: string;
  ok: boolean;
  summary: string;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  reply: string;
  trace: ChatTraceStep[];
}
