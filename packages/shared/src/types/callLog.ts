export type CallStatus = "queued" | "ringing" | "in_progress" | "ended" | "failed";

export type ResolutionStatus =
  | "resolved"
  | "follow_up_required"
  | "escalated"
  | "unknown"
  | "not_connected";

export interface ActionTaken {
  tool: string;
  ok: boolean;
  summary: string;
}

export interface CallLogSummary {
  id: number;
  astrologer_id: number;
  astrologer_name: string;
  priority: number | null;
  phone_number: string;
  triggered_by: string;
  ticket_id: number | null;
  created_ticket_id: number | null;
  status: CallStatus;
  ended_reason: string | null;
  resolution_status: ResolutionStatus | null;
  support_summary: string | null;
  created_at: string;
  ended_at: string | null;
}

export interface CallLogDetail extends CallLogSummary {
  transcript: string | null;
  suggested_solution: string | null;
  next_action: string | null;
  actions_taken: ActionTaken[] | null;
}
