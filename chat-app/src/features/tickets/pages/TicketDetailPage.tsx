import { Link, useParams } from "react-router-dom";

import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useTicket } from "../api/useTicket";
import { TicketStatusBadge } from "../components/TicketStatusBadge";
import { TicketTimeline } from "../components/TicketTimeline";

export function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const ticketId = Number(id);
  const { data: ticket, status } = useTicket(ticketId);

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-2 border-b border-night/10 bg-white px-4 py-3">
        <Link to="/tickets" className="text-night/50" aria-label="Back to My Tickets">
          <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5">
            <path
              d="M15 5 8 12l7 7"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </Link>
        <h1 className="text-lg font-medium text-night">Ticket #{ticketId}</h1>
      </header>
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {status === "pending" && <Spinner label="Loading ticket…" />}
        {status === "error" && <EmptyState title="Couldn't load this ticket" />}
        {status === "success" && (
          <div className="flex flex-col gap-4">
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium capitalize text-night">
                  {ticket.category.replace(/_/g, " ")}
                </span>
                <TicketStatusBadge status={ticket.status} />
              </div>
              <p className="text-sm text-night/70">{ticket.description}</p>
            </div>
            <TicketTimeline ticket={ticket} />
          </div>
        )}
      </div>
    </div>
  );
}
