import type { CallLogSummary } from "@astrohelp/shared";
import { Link, useNavigate } from "react-router-dom";

import { CallStatusBadge } from "./CallStatusBadge";
import { ResolutionStatusBadge } from "./ResolutionStatusBadge";

function PriorityBadge({ priority }: { priority: number | null }) {
  if (priority === null) return <span className="text-xs text-night/30">—</span>;
  const isVip = priority <= 2;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
        isVip ? "bg-clay-100 text-clay-700" : "bg-slate-100 text-slate-600"
      }`}
    >
      P{priority}
    </span>
  );
}

function formatDuration(createdAt: string, endedAt: string | null): string {
  if (!endedAt) return "In progress";
  const seconds = Math.round((new Date(endedAt).getTime() - new Date(createdAt).getTime()) / 1000);
  if (seconds < 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function truncate(text: string | null, max: number): string {
  if (!text) return "—";
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

export function CallLogsTable({ calls }: { calls: CallLogSummary[] }) {
  const navigate = useNavigate();

  return (
    <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
            <th className="px-4 py-3 font-medium">Astrologer</th>
            <th className="px-4 py-3 font-medium">Priority</th>
            <th className="px-4 py-3 font-medium">Resolution</th>
            <th className="px-4 py-3 font-medium">Summary</th>
            <th className="px-4 py-3 font-medium">Duration</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Ticket</th>
            <th className="px-4 py-3 font-medium">Date</th>
          </tr>
        </thead>
        <tbody>
          {calls.map((call) => {
            const ticketId = call.ticket_id ?? call.created_ticket_id;
            return (
              <tr
                key={call.id}
                onClick={() => navigate(`/call-logs/${call.id}`)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter") navigate(`/call-logs/${call.id}`);
                }}
                className="cursor-pointer border-b border-night/5 last:border-0 hover:bg-cream/60"
              >
                <td className="px-4 py-3">
                  <p className="font-medium text-night">{call.astrologer_name}</p>
                  <p className="text-xs text-night/40">#{call.astrologer_id}</p>
                </td>
                <td className="px-4 py-3">
                  <PriorityBadge priority={call.priority} />
                </td>
                <td className="px-4 py-3">
                  <ResolutionStatusBadge status={call.resolution_status} />
                </td>
                <td className="max-w-xs px-4 py-3 text-night/70">
                  {truncate(call.support_summary, 80)}
                </td>
                <td className="px-4 py-3 text-xs text-night/50">
                  {formatDuration(call.created_at, call.ended_at)}
                </td>
                <td className="px-4 py-3">
                  <CallStatusBadge status={call.status} />
                </td>
                <td className="px-4 py-3">
                  {ticketId ? (
                    <Link
                      to={`/tickets/${ticketId}`}
                      onClick={(e) => e.stopPropagation()}
                      className="font-medium text-terracotta hover:underline"
                    >
                      #{ticketId}
                    </Link>
                  ) : (
                    <span className="text-xs text-night/30">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-night/50">
                  {new Date(call.created_at).toLocaleString(undefined, {
                    day: "numeric",
                    month: "short",
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
