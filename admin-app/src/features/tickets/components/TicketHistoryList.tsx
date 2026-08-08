import { STATUS_LABELS, type TicketStatusHistoryEntry } from "@astrohelp/shared";

export function TicketHistoryList({ history }: { history: TicketStatusHistoryEntry[] }) {
  return (
    <div className="rounded-xl border border-night/10 p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-night/40">History</p>
      <ol className="flex flex-col gap-3">
        {history.map((entry, i) => (
          <li key={i} className="text-sm">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-medium text-night">{STATUS_LABELS[entry.status]}</span>
              <span className="text-xs text-night/40">
                {new Date(entry.changed_at).toLocaleString(undefined, {
                  day: "numeric",
                  month: "short",
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </span>
            </div>
            <p className="text-xs text-night/50">by {entry.changed_by}</p>
            {entry.note && <p className="mt-0.5 text-sm text-night/70">{entry.note}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}
