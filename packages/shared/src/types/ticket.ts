export type TicketStatus =
  | "submitted"
  | "assigned_to_kam"
  | "under_review"
  | "in_progress"
  | "resolved"
  | "closed";

export interface TicketStatusHistoryEntry {
  status: TicketStatus;
  changed_at: string;
  changed_by: string;
  note: string | null;
  // False for an ownership/escalation log entry (reassignment, escalation)
  // that reuses the ticket's current status verbatim rather than actually
  // changing it — chat-app must never announce these to the astrologer as
  // if they were a real status update (an escalation note is for the KAM).
  is_status_change: boolean;
}

export interface Ticket {
  id: number;
  astrologer_id: number;
  category: string;
  sub_category: string;
  description: string;
  description_en: string;
  preferred_language: string;
  attachment_url: string | null;
  assigned_admin_id: number | null;
  assigned_cs_id: number | null;
  kam_notified: boolean;
  cs_notified: boolean;
  status: TicketStatus;
  resolved_at: string | null;
  satisfaction: "satisfied" | "unsatisfied" | null;
  // The astrologer's 1-5 star rating of the most recent resolution —
  // >=4 is what sets satisfaction to "satisfied" (see backend's
  // record_ticket_rating). reasons/comment/rated_at are null until rated,
  // and reset back to null on any later resolve/reopen cycle.
  rating: number | null;
  rating_reasons: string[] | null;
  rating_comment: string | null;
  rated_at: string | null;
  // Set by a CS escalating to the KAM (see the "Escalate to KAM" action) —
  // excludes this ticket from a CS's "resolved" tally in analytics even
  // though assigned_cs_id doesn't change.
  escalated_to_kam: boolean;
  escalated_at: string | null;
  created_at: string;
  updated_at: string;
  history: TicketStatusHistoryEntry[];
}
