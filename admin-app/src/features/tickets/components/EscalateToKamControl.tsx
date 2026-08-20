import { useState } from "react";

import { Button } from "../../../components/Button";
import { useEscalateTicket } from "../api/useEscalateTicket";

export function EscalateToKamControl({
  ticketId,
  escalatedToKam,
}: {
  ticketId: number;
  escalatedToKam: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const escalate = useEscalateTicket(ticketId);

  if (escalatedToKam) {
    return (
      <div className="rounded-xl border border-ochre/20 bg-ochre-100/40 p-4">
        <p className="text-sm font-medium text-ochre-700">Escalated to KAM</p>
      </div>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-sm font-medium text-terracotta hover:underline"
      >
        Escalate to KAM
      </button>
    );
  }

  const trimmed = note.trim();

  return (
    <div className="rounded-xl border border-night/10 p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-night/40">
        Escalate to KAM
      </p>
      <div className="flex flex-col gap-2.5">
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Why does this need the KAM? (required)"
          rows={3}
          className="w-full resize-none rounded-lg border border-night/15 px-3 py-2 text-sm text-ink placeholder:text-night/40 focus-visible:border-terracotta"
        />
        <div className="flex gap-2">
          <Button
            onClick={() =>
              escalate.mutate(trimmed, {
                onSuccess: () => {
                  setOpen(false);
                  setNote("");
                },
              })
            }
            disabled={!trimmed || escalate.isPending}
          >
            {escalate.isPending ? "Escalating…" : "Confirm escalation"}
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setOpen(false);
              setNote("");
            }}
          >
            Cancel
          </Button>
        </div>
        {escalate.isError && <p className="text-sm text-clay">Couldn't escalate — please try again.</p>}
      </div>
    </div>
  );
}
