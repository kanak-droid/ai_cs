import { useState } from "react";

import { ReassignTicketForm } from "./ReassignTicketForm";

export function ReassignTicketControl({ ticketId }: { ticketId: number }) {
  const [open, setOpen] = useState(false);

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
