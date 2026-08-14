import type { Astrologer } from "./astrologer";
import type { Ticket } from "./ticket";

export type AdminRole = "kam" | "cs" | "others";
export type AdminAccessLevel = "normal" | "admin";

export interface Admin {
  id: number;
  name: string;
  email: string;
  slack_channel: string;
  role: AdminRole;
  access_level: AdminAccessLevel;
  languages: string[];
  is_active: boolean;
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
}
