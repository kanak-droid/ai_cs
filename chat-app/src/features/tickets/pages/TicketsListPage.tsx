import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useTickets } from "../api/useTickets";
import { TicketList } from "../components/TicketList";

export function TicketsListPage() {
  const { data: tickets, status } = useTickets();

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-night/10 bg-white px-4 py-3">
        <h1 className="text-lg font-medium text-night">My Tickets</h1>
      </header>
      <div className="flex-1 overflow-y-auto">
        {status === "pending" && <Spinner label="Loading your tickets…" />}
        {status === "error" && (
          <EmptyState title="Couldn't load your tickets" description="Please try again shortly." />
        )}
        {status === "success" && tickets.length === 0 && (
          <EmptyState
            title="No tickets yet"
            description="When you raise an issue in chat, you'll be able to track it here."
          />
        )}
        {status === "success" && tickets.length > 0 && <TicketList tickets={tickets} />}
      </div>
    </div>
  );
}
