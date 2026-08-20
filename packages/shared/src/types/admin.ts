import type { Astrologer } from "./astrologer";
import type { Ticket } from "./ticket";

export type AdminRole = "kam" | "cs" | "others";
export type AdminAccessLevel = "normal" | "admin";

export interface Admin {
  id: number;
  name: string;
  email: string;
  slack_channel: string;
  // Slack's own member id (e.g. "U0123ABC456") — needed to build a real
  // <@U0123ABC456> mention, the only syntax Slack renders as a highlighted,
  // notifying mention. Null until someone fills it in on the Admins page.
  slack_user_id: string | null;
  role: AdminRole;
  access_level: AdminAccessLevel;
  languages: string[];
  is_active: boolean;
  // Temporary, reversible "on leave" state — distinct from is_active
  // (permanent deactivation). Stays is_active=true while on leave, so they
  // keep showing everywhere an active admin does; only excluded from NEW
  // ticket round-robin. See backend Admin model's docstring.
  is_temporarily_inactive: boolean;
}

export interface AdminTicket extends Ticket {
  astrologer: Astrologer;
}

export interface SlackLogEntry {
  id: number;
  channel: string;
  message: string;
  ticket_id: number | null;
  sent_at: string;
  mock: boolean;
}

export interface EmailLogEntry {
  id: number;
  to_email: string;
  subject: string;
  body: string;
  sent_at: string;
  mock: boolean;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface KamPerformance {
  admin_id: number;
  name: string;
  role: AdminRole;
  pending_count: number;
  assigned_count: number;
  solved_count: number;
  // Only meaningful for CS rows — tickets they escalated to the KAM,
  // already excluded from solved_count above. Always 0 for KAM rows.
  escalated_to_kam_count: number;
  // Average hours from ticket creation to resolution, for tickets they
  // solved — null if they haven't solved any yet.
  avg_tat_hours: number | null;
}

export type PriorityFilter = "1" | "2" | "3" | "4" | "5" | "unranked";

export interface TicketPeriodCount {
  // ISO date of the bucket's start (e.g. the Monday of that week, or the
  // 1st of that month) — a plain string, used directly as a chart axis label.
  period: string;
  created_count: number;
  resolved_count: number;
}

export interface AnalyticsOverview {
  bot_resolved_count: number;
  escalated_count: number;
  top_categories: CategoryCount[];
  avg_bot_resolution_seconds: number | null;
  avg_ticket_resolution_hours: number | null;
  satisfied_count: number;
  unsatisfied_count: number;
  avg_bot_rating: number | null;
  rating_distribution: Record<string, number>;
  kam_performance: KamPerformance[];
  weekly_ticket_trend: TicketPeriodCount[];
  monthly_ticket_trend: TicketPeriodCount[];
}
