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
  // Set by a CS escalating to the KAM (see the "Escalate to KAM" action) —
  // excludes this ticket from a CS's "resolved" tally in analytics even
  // though assigned_cs_id doesn't change.
  escalated_to_kam: boolean;
  escalated_at: string | null;
  created_at: string;
  updated_at: string;
  history: TicketStatusHistoryEntry[];
}
