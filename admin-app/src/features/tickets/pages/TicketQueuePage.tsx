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
    sort: (searchParams.get("sort") as "asc" | "desc" | "priority") ?? "desc",
  };

  const { data: tickets, status } = useTicketQueue(filters);

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
      {status === "success" && tickets.length > 0 && <TicketQueueTable tickets={tickets} />}
    </div>
  );
}
