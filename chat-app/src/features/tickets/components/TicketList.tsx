import type { Ticket } from "@astrohelp/shared";
import { Link } from "react-router-dom";

import { TicketStatusBadge } from "./TicketStatusBadge";

export function TicketList({ tickets }: { tickets: Ticket[] }) {
  return (
    <ul className="flex flex-col gap-2 px-4 py-4">
      {tickets.map((ticket) => (
        <li key={ticket.id}>
          <Link
            to={`/tickets/${ticket.id}`}
            className="flex flex-col gap-1.5 rounded-2xl bg-white p-4 shadow-sm transition-colors hover:bg-cloudline/60"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium capitalize text-night">
                {ticket.category.replace(/_/g, " ")}
              </span>
              <TicketStatusBadge status={ticket.status} />
            </div>
            <p className="line-clamp-2 text-sm text-night/60">{ticket.description_en}</p>
            <p className="text-xs text-night/40">
              {new Date(ticket.created_at).toLocaleDateString(undefined, {
                day: "numeric",
                month: "short",
                year: "numeric",
              })}
            </p>
          </Link>
        </li>
      ))}
    </ul>
  );
}
