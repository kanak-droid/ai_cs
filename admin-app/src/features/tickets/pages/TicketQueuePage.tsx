import { useSearchParams } from "react-router-dom";

import { useAuth } from "../../../auth/AuthContext";
import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useTicketQueue } from "../api/useTicketQueue";
import { TicketFilters } from "../components/TicketFilters";
import { TicketQueueTable } from "../components/TicketQueueTable";

export function TicketQueuePage() {
  const [searchParams] = useSearchParams();
  const { admin } = useAuth();

  // Absent param -> default to "my tickets". Explicit "all" -> unfiltered.
  const assignedParam = searchParams.get("assigned_admin_id");
  const assignedAdminId =
    assignedParam === "all"
      ? undefined
      : assignedParam
        ? Number(assignedParam)
        : admin?.adminId;

  const filters = {
    status: searchParams.get("status") ?? undefined,
    assignedAdminId,
    // Always highest-priority-first (P1 at top) — there's no sort control
    // for this anymore; priority is what actually determines urgency here.
    sort: "priority" as const,
    dateFrom: searchParams.get("from") ?? undefined,
    dateTo: searchParams.get("to") ?? undefined,
  };

  const { data: tickets, status } = useTicketQueue(filters);

  const activeTickets = tickets?.filter((t) => t.status !== "resolved" && t.status !== "closed") ?? [];
  const closedTickets = tickets?.filter((t) => t.status === "resolved" || t.status === "closed") ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-night">Tickets</h1>
          <p className="text-sm text-night/50">
            {status === "success" ? `${tickets.length} ticket${tickets.length === 1 ? "" : "s"}` : ""}
          </p>
        </div>
        <TicketFilters />
      </div>

      {status === "pending" && <Spinner label="Loading tickets…" />}
      {status === "error" && <EmptyState title="Couldn't load tickets" />}
      {status === "success" && tickets.length === 0 && (
        <EmptyState title="No tickets match these filters" />
      )}
      {status === "success" && tickets.length > 0 && (
        <>
          {activeTickets.length > 0 ? (
            <TicketQueueTable tickets={activeTickets} />
          ) : (
            <p className="text-sm text-night/40">No active tickets — everything's resolved.</p>
          )}

          <div className="mt-2 flex flex-col gap-2">
            <h2 className="text-sm font-medium uppercase tracking-wide text-night/40">
              Resolved ({closedTickets.length})
            </h2>
            {closedTickets.length === 0 ? (
              <p className="text-sm text-night/40">No resolved tickets yet.</p>
            ) : (
              <TicketQueueTable tickets={closedTickets} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
