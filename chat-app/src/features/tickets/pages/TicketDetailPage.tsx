import { Link, useParams } from "react-router-dom";

import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useSubmitTicketRating } from "../api/useSubmitTicketRating";
import { useTicket } from "../api/useTicket";
import { TicketRatingWidget } from "../components/TicketRatingWidget";
import { TicketStatusBadge } from "../components/TicketStatusBadge";
import { TicketTimeline } from "../components/TicketTimeline";

export function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const ticketId = Number(id);
  const { data: ticket, status } = useTicket(ticketId);
  const submitTicketRating = useSubmitTicketRating();

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
        <h1 className="font-display text-xl font-semibold text-night">Ticket #{ticketId}</h1>
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
            {ticket.status === "resolved" && !ticket.satisfaction && (
              // Shows regardless of how the astrologer got here — including
              // landing directly on this route from a push notification —
              // since it's driven entirely by the ticket's own state, not
              // by any query param this page has to know about.
              <TicketRatingWidget
                ticketId={ticket.id}
                onSubmit={(id, rating, reasons, comment) =>
                  submitTicketRating.mutate({ id, rating, reasons, comment })
                }
              />
            )}
            {submitTicketRating.data?.id === ticket.id &&
              submitTicketRating.data.status === "under_review" && (
                <p className="text-sm text-night/60">
                  We've reopened this ticket for another look.{" "}
                  <Link to="/" className="font-medium text-terracotta underline">
                    Open chat
                  </Link>{" "}
                  to tell us more.
                </p>
              )}
          </div>
        )}
      </div>
    </div>
  );
}
