import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { CallStatusBadge } from "../../callLogs/components/CallStatusBadge";
import { ResolutionStatusBadge } from "../../callLogs/components/ResolutionStatusBadge";
import { fetchAstrologerOverview, searchAstrologers } from "../api/astrologersApi";

import type { Astrologer, CallLogSummary, ChatSessionSummary, Ticket } from "@astrohelp/shared";

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

function TicketStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    submitted: "bg-ochre-100 text-ochre-700",
    assigned_to_kam: "bg-blue-100 text-blue-700",
    under_review: "bg-blue-100 text-blue-700",
    in_progress: "bg-blue-100 text-blue-700",
    resolved: "bg-moss-100 text-moss-700",
    closed: "bg-slate-100 text-slate-600",
  };
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function ChatResolutionBadge({ resolvedBy }: { resolvedBy: string | null }) {
  if (!resolvedBy)
    return <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">Active</span>;
  if (resolvedBy === "bot")
    return <span className="rounded-full bg-moss-100 px-2 py-0.5 text-xs font-medium text-moss-700">Resolved by bot</span>;
  return <span className="rounded-full bg-ochre-100 px-2 py-0.5 text-xs font-medium text-ochre-700">Escalated</span>;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

function TicketsTable({ tickets }: { tickets: Ticket[] }) {
  const navigate = useNavigate();
  if (!tickets.length) return <p className="py-4 text-center text-sm text-night/40">No tickets</p>;
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
          <th className="px-3 py-2 font-medium">#</th>
          <th className="px-3 py-2 font-medium">Category</th>
          <th className="px-3 py-2 font-medium">Status</th>
          <th className="px-3 py-2 font-medium">Date</th>
        </tr>
      </thead>
      <tbody>
        {tickets.map((t) => (
          <tr
            key={t.id}
            onClick={() => navigate(`/tickets/${t.id}`)}
            className="cursor-pointer border-b border-night/5 last:border-0 hover:bg-cream/60"
          >
            <td className="px-3 py-2 font-medium text-terracotta">#{t.id}</td>
            <td className="px-3 py-2 text-night/70">{t.category}</td>
            <td className="px-3 py-2"><TicketStatusBadge status={t.status} /></td>
            <td className="px-3 py-2 text-xs text-night/50">{formatDate(t.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CallsTable({ calls }: { calls: CallLogSummary[] }) {
  const navigate = useNavigate();
  if (!calls.length) return <p className="py-4 text-center text-sm text-night/40">No calls</p>;
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
          <th className="px-3 py-2 font-medium">#</th>
          <th className="px-3 py-2 font-medium">Resolution</th>
          <th className="px-3 py-2 font-medium">Status</th>
          <th className="px-3 py-2 font-medium">Summary</th>
          <th className="px-3 py-2 font-medium">Date</th>
        </tr>
      </thead>
      <tbody>
        {calls.map((c) => (
          <tr
            key={c.id}
            onClick={() => navigate(`/call-logs/${c.id}`)}
            className="cursor-pointer border-b border-night/5 last:border-0 hover:bg-cream/60"
          >
            <td className="px-3 py-2 font-medium text-terracotta">#{c.id}</td>
            <td className="px-3 py-2"><ResolutionStatusBadge status={c.resolution_status} /></td>
            <td className="px-3 py-2"><CallStatusBadge status={c.status} /></td>
            <td className="max-w-xs px-3 py-2 text-night/70 truncate">{c.support_summary ?? "—"}</td>
            <td className="px-3 py-2 text-xs text-night/50">{formatDate(c.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ChatSessionsTable({ sessions }: { sessions: ChatSessionSummary[] }) {
  const navigate = useNavigate();
  if (!sessions.length) return <p className="py-4 text-center text-sm text-night/40">No chat sessions</p>;
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
          <th className="px-3 py-2 font-medium">#</th>
          <th className="px-3 py-2 font-medium">Category</th>
          <th className="px-3 py-2 font-medium">Resolution</th>
          <th className="px-3 py-2 font-medium">Ticket</th>
          <th className="px-3 py-2 font-medium">Date</th>
        </tr>
      </thead>
      <tbody>
        {sessions.map((s) => (
          <tr
            key={s.id}
            onClick={() => navigate(`/chat-logs/${s.id}`)}
            className="cursor-pointer border-b border-night/5 last:border-0 hover:bg-cream/60"
          >
            <td className="px-3 py-2 font-medium text-terracotta">#{s.id}</td>
            <td className="px-3 py-2 text-night/70">{s.category ?? "—"}</td>
            <td className="px-3 py-2"><ChatResolutionBadge resolvedBy={s.resolved_by} /></td>
            <td className="px-3 py-2">
              {s.ticket_id ? (
                <Link to={`/tickets/${s.ticket_id}`} onClick={(e) => e.stopPropagation()} className="font-medium text-terracotta hover:underline">
                  #{s.ticket_id}
                </Link>
              ) : (
                <span className="text-xs text-night/30">—</span>
              )}
            </td>
            <td className="px-3 py-2 text-xs text-night/50">{formatDate(s.started_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function AstrologerOverviewPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: results } = useQuery({
    queryKey: ["admin", "astrologer-search", searchQuery],
    queryFn: () => searchAstrologers(searchQuery),
    enabled: searchQuery.length >= 1,
    staleTime: 10_000,
  });

  const { data: overview, status } = useQuery({
    queryKey: ["admin", "astrologer-overview", selectedId],
    queryFn: () => fetchAstrologerOverview(selectedId!),
    enabled: selectedId !== null,
  });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-semibold text-night">Astrologer Overview</h1>
        <p className="text-sm text-night/50">
          Full support history for any astrologer — tickets, calls, and chats in one place.
        </p>
      </div>

      <div className="relative max-w-md">
        <input
          type="text"
          placeholder="Search by astrologer name or ID..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            if (!e.target.value) setSelectedId(null);
          }}
          className="w-full rounded-xl border border-night/15 px-4 py-3 text-sm text-ink placeholder:text-night/30 focus-visible:border-terracotta focus-visible:outline-none"
        />
        {searchQuery && !selectedId && results && results.length > 0 && (
          <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-60 overflow-auto rounded-xl border border-night/10 bg-white shadow-lg">
            {results.map((a: Astrologer) => (
              <button
                key={a.id}
                type="button"
                onClick={() => {
                  setSelectedId(a.id);
                  setSearchQuery(a.name);
                }}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm hover:bg-cream/60"
              >
                <span className="font-medium text-night">{a.name}</span>
                <span className="text-night/40">#{a.id}</span>
                {a.priority !== null && (
                  <span className="ml-auto text-xs text-night/40">P{a.priority}</span>
                )}
              </button>
            ))}
          </div>
        )}
        {searchQuery && !selectedId && results && results.length === 0 && (
          <div className="absolute left-0 right-0 top-full z-10 mt-1 rounded-xl border border-night/10 bg-white px-4 py-3 text-sm text-night/40 shadow-lg">
            No astrologers found
          </div>
        )}
      </div>

      {selectedId && status === "pending" && <Spinner label="Loading overview..." />}
      {selectedId && status === "error" && <EmptyState title="Couldn't load astrologer data" />}

      {overview && (
        <>
          <div className="rounded-2xl bg-white p-5 shadow-sm">
            <div className="flex items-center gap-4">
              <div>
                <h2 className="font-display text-xl font-semibold text-night">
                  {overview.astrologer.name}
                </h2>
                <p className="text-sm text-night/50">
                  #{overview.astrologer.id} · {overview.astrologer.phone} · {overview.astrologer.language}
                </p>
              </div>
              <PriorityBadge priority={overview.astrologer.priority} />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-4">
              <div className="rounded-xl bg-cream/50 p-3 text-center">
                <p className="font-display text-2xl font-semibold text-night">{overview.tickets.length}</p>
                <p className="text-xs text-night/50">Tickets</p>
              </div>
              <div className="rounded-xl bg-cream/50 p-3 text-center">
                <p className="font-display text-2xl font-semibold text-night">{overview.calls.length}</p>
                <p className="text-xs text-night/50">AI Calls</p>
              </div>
              <div className="rounded-xl bg-cream/50 p-3 text-center">
                <p className="font-display text-2xl font-semibold text-night">{overview.chat_sessions.length}</p>
                <p className="text-xs text-night/50">Chat Sessions</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div className="rounded-2xl bg-white shadow-sm">
              <h3 className="border-b border-night/10 px-4 py-3 text-sm font-semibold text-night">
                Tickets ({overview.tickets.length})
              </h3>
              <TicketsTable tickets={overview.tickets} />
            </div>

            <div className="rounded-2xl bg-white shadow-sm">
              <h3 className="border-b border-night/10 px-4 py-3 text-sm font-semibold text-night">
                AI Calls ({overview.calls.length})
              </h3>
              <CallsTable calls={overview.calls} />
            </div>

            <div className="rounded-2xl bg-white shadow-sm">
              <h3 className="border-b border-night/10 px-4 py-3 text-sm font-semibold text-night">
                Chat Sessions ({overview.chat_sessions.length})
              </h3>
              <ChatSessionsTable sessions={overview.chat_sessions} />
            </div>
          </div>
        </>
      )}

      {!selectedId && !searchQuery && (
        <EmptyState
          title="Search for an astrologer"
          description="Type a name or ID above to see their full support history."
        />
      )}
    </div>
  );
}
