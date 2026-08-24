import { useState } from "react";

import { Button } from "../../../components/Button";
import { useAdminsLookup } from "../api/useAdminsLookup";
import { useBulkReassignTickets } from "../api/useBulkReassignTickets";

// Deliberately a near-duplicate of ReassignTicketForm rather than a shared
// abstraction over both: the single-ticket flow calls a different mutation
// shape (one ticket) with its own onDone/onCancel contract already wired
// into two existing call sites (ticket detail page, single-row modal) —
// refactoring it to also serve a many-tickets mutation risked destabilizing
// a form that's already working in production for a fairly small amount of
// saved code.
export function BulkReassignForm({
  ticketIds,
  onDone,
  onCancel,
}: {
  ticketIds: number[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const [role, setRole] = useState<"kam" | "cs">("kam");
  const [adminId, setAdminId] = useState("");
  const [note, setNote] = useState("");
  const { data: admins } = useAdminsLookup();
  const bulkReassign = useBulkReassignTickets();

  const candidates = admins?.filter((a) => a.role === role && !a.is_temporarily_inactive) ?? [];
  const failures = bulkReassign.data?.results.filter((r) => !r.ok) ?? [];

  function handleConfirm() {
    if (!adminId) return;
    bulkReassign.mutate(
      { ticketIds, role, adminId: Number(adminId), note: note.trim() || undefined },
      {
        onSuccess: (data) => {
          // Only auto-close on a clean sweep — if some tickets failed
          // (e.g. one had already moved to a different role), keep the
          // modal open so that per-ticket error list stays visible.
          if (data.results.every((r) => r.ok)) onDone();
        },
      },
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      <p className="text-sm text-night/60">
        Reassigning {ticketIds.length} ticket{ticketIds.length === 1 ? "" : "s"} at once.
      </p>
      <select
        value={role}
        onChange={(e) => {
          setRole(e.target.value as "kam" | "cs");
          setAdminId("");
        }}
        className="w-full rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
      >
        <option value="kam">KAM</option>
        <option value="cs">CS</option>
      </select>
      <select
        value={adminId}
        onChange={(e) => setAdminId(e.target.value)}
        className="w-full rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
      >
        <option value="">Select a {role === "kam" ? "KAM" : "CS"}…</option>
        {candidates.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Reason (optional)"
        rows={2}
        className="w-full resize-none rounded-lg border border-night/15 px-3 py-2 text-sm text-ink placeholder:text-night/40 focus-visible:border-terracotta"
      />
      <div className="flex gap-2">
        <Button onClick={handleConfirm} disabled={!adminId || bulkReassign.isPending}>
          {bulkReassign.isPending ? "Reassigning…" : `Reassign ${ticketIds.length} ticket(s)`}
        </Button>
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
      {bulkReassign.isError && (
        <p className="text-sm text-clay">Couldn't reassign — please try again.</p>
      )}
      {failures.length > 0 && (
        <div className="rounded-lg bg-clay-100/60 p-2.5 text-sm text-clay-700">
          <p className="font-medium">{failures.length} ticket(s) couldn't be reassigned:</p>
          <ul className="mt-1 list-inside list-disc">
            {failures.map((f) => (
              <li key={f.ticket_id}>
                #{f.ticket_id}: {f.error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
