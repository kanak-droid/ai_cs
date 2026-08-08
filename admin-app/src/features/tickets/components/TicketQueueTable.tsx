import type { AdminTicket } from "@astrohelp/shared";
import { useNavigate } from "react-router-dom";

import { TicketStatusBadge } from "./TicketStatusBadge";

export function TicketQueueTable({ tickets }: { tickets: AdminTicket[] }) {
  const navigate = useNavigate();

  return (
    <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
            <th className="px-4 py-3 font-medium">Astrologer</th>
            <th className="px-4 py-3 font-medium">Issue</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr
              key={ticket.id}
              onClick={() => navigate(`/tickets/${ticket.id}`)}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") navigate(`/tickets/${ticket.id}`);
              }}
              className="cursor-pointer border-b border-night/5 last:border-0 hover:bg-cream/60"
            >
              <td className="px-4 py-3">
                <p className="font-medium text-night">{ticket.astrologer.name}</p>
                <p className="text-xs text-night/40">#{ticket.astrologer_id}</p>
              </td>
              <td className="px-4 py-3">
                <p className="capitalize text-night">{ticket.category.replace(/_/g, " ")}</p>
                <p className="max-w-xs truncate text-xs text-night/50">{ticket.description_en}</p>
              </td>
              <td className="px-4 py-3">
                <TicketStatusBadge status={ticket.status} />
              </td>
              <td className="px-4 py-3 text-xs text-night/50">
                {new Date(ticket.created_at).toLocaleDateString(undefined, {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
