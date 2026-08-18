import type { ChatSessionSummary } from "@astrohelp/shared";
import { useNavigate } from "react-router-dom";

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

function ResolutionBadge({ resolvedBy }: { resolvedBy: string | null }) {
  if (resolvedBy === null) {
    return (
      <span className="inline-flex items-center rounded-full bg-terracotta-100 px-2.5 py-1 text-xs font-medium text-terracotta-700">
        Active
      </span>
    );
  }
  if (resolvedBy === "bot") {
    return (
      <span className="inline-flex items-center rounded-full bg-moss-100 px-2.5 py-1 text-xs font-medium text-moss-700">
        Resolved by bot
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-night/10 px-2.5 py-1 text-xs font-medium text-night/60">
      Escalated to ticket
    </span>
  );
}

export function ChatSessionsTable({ sessions }: { sessions: ChatSessionSummary[] }) {
  const navigate = useNavigate();

  return (
    <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
            <th className="px-4 py-3 font-medium">Astrologer</th>
            <th className="px-4 py-3 font-medium">Priority</th>
            <th className="px-4 py-3 font-medium">Issue</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Started</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => (
            <tr
              key={session.id}
              onClick={() => navigate(`/chat-logs/${session.id}`)}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") navigate(`/chat-logs/${session.id}`);
              }}
              className="cursor-pointer border-b border-night/5 last:border-0 hover:bg-cream/60"
            >
              <td className="px-4 py-3">
                <p className="font-medium text-night">{session.astrologer_name}</p>
                <p className="text-xs text-night/40">#{session.astrologer_id}</p>
              </td>
              <td className="px-4 py-3">
                <PriorityBadge priority={session.priority} />
              </td>
              <td className="px-4 py-3">
                {session.category ? (
                  <p className="capitalize text-night">{session.category.replace(/_/g, " ")}</p>
                ) : (
                  <span className="text-xs text-night/30">—</span>
                )}
              </td>
              <td className="px-4 py-3">
                <ResolutionBadge resolvedBy={session.resolved_by} />
              </td>
              <td className="px-4 py-3 text-xs text-night/50">
                {new Date(session.started_at).toLocaleString(undefined, {
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
