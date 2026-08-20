import { useState } from "react";

import { useAuth } from "../../../auth/AuthContext";
import { ReassignTicketForm } from "./ReassignTicketForm";

export function ReassignTicketControl({ ticketId }: { ticketId: number }) {
  const [open, setOpen] = useState(false);
  const { admin } = useAuth();

  // Reassigning ownership is an ADMIN-access-level action (see the
  // matching backend gate on POST .../reassign) — a normal-access KAM/CS
  // shouldn't even see the option.
  if (admin?.accessLevel !== "admin") return null;

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-sm font-medium text-terracotta hover:underline"
      >
        Reassign this ticket
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-night/10 p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-night/40">Reassign ticket</p>
      <ReassignTicketForm ticketId={ticketId} onDone={() => setOpen(false)} onCancel={() => setOpen(false)} />
    </div>
  );
}
