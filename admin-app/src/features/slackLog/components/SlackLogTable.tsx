import type { SlackLogEntry } from "@astrohelp/shared";

export function SlackLogTable({ entries }: { entries: SlackLogEntry[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
            <th className="px-4 py-3 font-medium">Channel</th>
            <th className="px-4 py-3 font-medium">Message</th>
            <th className="px-4 py-3 font-medium">Ticket</th>
            <th className="px-4 py-3 font-medium">Sent</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id} className="border-b border-night/5 last:border-0">
              <td className="px-4 py-3 font-medium text-night">{entry.channel}</td>
              <td className="max-w-md px-4 py-3 text-night/70">{entry.message}</td>
              <td className="px-4 py-3 text-night/50">
                {entry.ticket_id ? `#${entry.ticket_id}` : "—"}
              </td>
              <td className="px-4 py-3 text-xs text-night/40">
                {new Date(entry.sent_at).toLocaleString(undefined, {
                  day: "numeric",
                  month: "short",
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
