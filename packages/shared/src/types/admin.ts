import type { Astrologer } from "./astrologer";
import type { Ticket } from "./ticket";

export interface Admin {
  id: number;
  name: string;
  email: string;
  slack_channel: string;
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
