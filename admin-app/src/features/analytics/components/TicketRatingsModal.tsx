import type { PriorityFilter } from "@astrohelp/shared";
import { Link } from "react-router-dom";

import { Modal } from "../../../components/Modal";
import { Spinner } from "../../../components/Spinner";
import { useTicketRatings } from "../api/useTicketRatings";

function Stars({ rating }: { rating: number }) {
  return (
    <span className="text-ochre" aria-label={`${rating} out of 5 stars`}>
      {"★".repeat(rating)}
      <span className="text-night/20">{"★".repeat(5 - rating)}</span>
    </span>
  );
}

export function TicketRatingsModal({
  onClose,
  priority,
  dateFrom,
  dateTo,
}: {
  onClose: () => void;
  priority?: PriorityFilter;
  dateFrom?: string;
  dateTo?: string;
}) {
  const { data: ratings, status } = useTicketRatings(true, priority, dateFrom, dateTo);

  return (
    <Modal title="Ticket ratings" onClose={onClose} size="lg">
      <div className="max-h-[70vh] overflow-y-auto">
        {status === "pending" && <Spinner label="Loading ratings…" />}
        {status === "error" && <p className="text-sm text-clay">Couldn't load ratings.</p>}
        {status === "success" && ratings.length === 0 && (
          <p className="text-sm text-night/50">No ratings yet for the current filters.</p>
        )}
        {status === "success" && ratings.length > 0 && (
          <ul className="flex flex-col gap-3">
            {ratings.map((entry) => (
              <li key={entry.ticket_id} className="rounded-xl border border-night/10 p-3">
                <div className="flex items-center justify-between gap-2">
                  <Link
                    to={`/tickets/${entry.ticket_id}`}
                    onClick={onClose}
                    className="text-sm font-medium text-terracotta hover:underline"
                  >
                    Ticket #{entry.ticket_id}
                  </Link>
                  <Stars rating={entry.rating} />
                </div>
                <p className="mt-0.5 text-xs text-night/50">
                  {entry.astrologer_name} · {entry.category.replace(/_/g, " ")} ·{" "}
                  {new Date(entry.rated_at).toLocaleDateString(undefined, {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                  })}
                </p>
                {entry.reasons.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {entry.reasons.map((reason) => (
                      <span
                        key={reason}
                        className="rounded-full bg-cream px-2 py-0.5 text-xs text-night/70"
                      >
                        {reason}
                      </span>
                    ))}
                  </div>
                )}
                {entry.comment && <p className="mt-2 text-sm text-night/70">"{entry.comment}"</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}
