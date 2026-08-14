import { STATUS_LABELS } from "@astrohelp/shared";

import { useTickets } from "../../tickets/api/useTickets";

// Surfaces the astrologer's most recent still-open ticket right in the chat —
// not just the separate "My Tickets" tab. Purely informational: the actual
// satisfied/unsatisfied ask happens as a proactive chat message the moment a
// ticket becomes resolved (see ChatPage's resolved-ticket watcher) rather
// than a button here the astrologer would have to notice on their own.
export function TicketStatusBanner() {
  const { data: tickets } = useTickets();

  const activeTicket = tickets?.find((t) => t.status !== "closed");
  if (!activeTicket) return null;

  return (
    <div className="border-t border-night/10 bg-white px-4 py-2">
      <p className="text-sm text-night/70">
        🎫 Ticket #{activeTicket.id} · <span className="font-medium text-night">{STATUS_LABELS[activeTicket.status]}</span>
      </p>
    </div>
  );
}
