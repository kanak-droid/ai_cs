import { useState } from "react";

import { Button } from "../../../components/Button";
import { useAdminsLookup } from "../api/useAdminsLookup";
import { useReassignTicket } from "../api/useReassignTicket";

// Pure form — no open/closed toggle of its own, so it can be dropped
// directly into either an inline expandable control (ticket detail page)
// or a Modal (ticket queue table), without duplicating the role/admin/note
// fields and the eligibility filtering in two places.
export function ReassignTicketForm({
  ticketId,
  onDone,
  onCancel,
}: {
  ticketId: number;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [role, setRole] = useState<"kam" | "cs">("kam");
  const [adminId, setAdminId] = useState("");
  const [note, setNote] = useState("");
  const { data: admins } = useAdminsLookup();
  const reassign = useReassignTicket(ticketId);

  // Only admins currently eligible for a new assignment — same bar as
  // round-robin (active, not on leave) — see admin_mapping_client/
  // cs_assignment_client and ticket_service.reassign_ticket.
  const candidates = admins?.filter((a) => a.role === role && !a.is_temporarily_inactive) ?? [];

  function handleConfirm() {
    if (!adminId) return;
    reassign.mutate(
      { role, adminId: Number(adminId), note: note.trim() || undefined },
      { onSuccess: onDone },
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
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
        <Button onClick={handleConfirm} disabled={!adminId || reassign.isPending}>
          {reassign.isPending ? "Reassigning…" : "Confirm reassignment"}
        </Button>
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
      {reassign.isError && <p className="text-sm text-clay">Couldn't reassign — please try again.</p>}
    </div>
  );
}
