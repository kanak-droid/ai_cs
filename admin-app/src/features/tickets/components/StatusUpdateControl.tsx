import { ADMIN_SETTABLE_STATUSES, STATUS_LABELS, type TicketStatus } from "@astrohelp/shared";
import { useState } from "react";

import { Button } from "../../../components/Button";
import { useUpdateTicketStatus } from "../api/useUpdateTicketStatus";

export function StatusUpdateControl({
  ticketId,
  currentStatus,
}: {
  ticketId: number;
  currentStatus: TicketStatus;
}) {
  const [nextStatus, setNextStatus] = useState<TicketStatus>(currentStatus);
  const [note, setNote] = useState("");
  const update = useUpdateTicketStatus(ticketId);

  const hasChange = nextStatus !== currentStatus;

  function handleConfirm() {
    update.mutate(
      { status: nextStatus, note: note.trim() || undefined },
      { onSuccess: () => setNote("") },
    );
  }

  return (
    <div className="rounded-xl border border-night/10 p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-night/40">Update status</p>
      <div className="flex flex-col gap-2.5">
        <select
          value={nextStatus}
          onChange={(e) => setNextStatus(e.target.value as TicketStatus)}
          className="rounded-lg border-night/15 text-sm text-ink focus-visible:border-harbor"
        >
          {ADMIN_SETTABLE_STATUSES.map((status) => (
            <option key={status} value={status}>
              {STATUS_LABELS[status]}
            </option>
          ))}
        </select>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Add a note (optional)"
          rows={2}
          className="resize-none rounded-lg border-night/15 text-sm text-ink placeholder:text-night/40 focus-visible:border-harbor"
        />
        <Button onClick={handleConfirm} disabled={!hasChange || update.isPending}>
          {update.isPending ? "Updating…" : `Confirm: mark as ${STATUS_LABELS[nextStatus]}`}
        </Button>
        {update.isError && <p className="text-sm text-clay">Couldn't update — please try again.</p>}
      </div>
    </div>
  );
}
