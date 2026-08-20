import { useState } from "react";

import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useChatSessions } from "../api/useChatSessions";
import { ChatSessionsTable } from "../components/ChatSessionsTable";

export function ChatLogsPage() {
  const { data: sessions, status } = useChatSessions();
  const [ticketSearch, setTicketSearch] = useState("");

  const trimmedSearch = ticketSearch.trim();
  // Searching by ticket number narrows to exactly the sessions that
  // escalated to a matching ticket — a session with no ticket never
  // matches, since there's nothing to search for.
  const matchingSessions = trimmedSearch
    ? sessions?.filter((s) => s.ticket_id !== null && String(s.ticket_id).includes(trimmedSearch))
    : sessions;

  const activeSessions = matchingSessions?.filter((s) => s.resolved_by === null) ?? [];
  const resolvedSessions = matchingSessions?.filter((s) => s.resolved_by !== null) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-night">Chatbot</h1>
          <p className="text-sm text-night/50">
            Every astrologer's conversation with the bot, sorted by priority — what issues they're
            facing, and what got resolved without a human.
          </p>
        </div>
        <input
          type="text"
          inputMode="numeric"
          value={ticketSearch}
          onChange={(e) => setTicketSearch(e.target.value)}
          placeholder="Search by ticket #"
          className="w-44 rounded-lg border border-night/15 px-3 py-2 text-sm text-ink placeholder:text-night/40 focus-visible:border-terracotta"
        />
      </div>

      {status === "pending" && <Spinner label="Loading chat logs…" />}
      {status === "error" && <EmptyState title="Couldn't load chat logs" />}
      {status === "success" && sessions.length === 0 && (
        <EmptyState title="No conversations yet" />
      )}
      {status === "success" && sessions.length > 0 && trimmedSearch && matchingSessions?.length === 0 && (
        <EmptyState title={`No conversation escalated to ticket #${trimmedSearch}`} />
      )}
      {status === "success" && sessions.length > 0 && (matchingSessions?.length ?? 0) > 0 && (
        <>
          <div>
            <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-night/40">
              Active ({activeSessions.length})
            </h2>
            {activeSessions.length === 0 ? (
              <p className="text-sm text-night/40">No active conversations right now.</p>
            ) : (
              <ChatSessionsTable sessions={activeSessions} />
            )}
          </div>

          <div className="mt-2 flex flex-col gap-2">
            <h2 className="text-sm font-medium uppercase tracking-wide text-night/40">
              Resolved ({resolvedSessions.length})
            </h2>
            {resolvedSessions.length === 0 ? (
              <p className="text-sm text-night/40">Nothing resolved yet.</p>
            ) : (
              <ChatSessionsTable sessions={resolvedSessions} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
