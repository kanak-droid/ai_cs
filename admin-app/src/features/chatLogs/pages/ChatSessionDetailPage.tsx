import { Link, useParams } from "react-router-dom";

import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useChatSessionDetail } from "../api/useChatSessionDetail";

export function ChatSessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);
  const { data: session, status } = useChatSessionDetail(sessionId);

  if (status === "pending") return <Spinner label="Loading conversation…" />;
  if (status === "error" || !session) return <EmptyState title="Couldn't load this conversation" />;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link to="/chat-logs" className="text-sm text-night/50 hover:text-night">
          ← Back to Chatbot
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <h1 className="font-display text-2xl font-semibold text-night">
            {session.astrologer_name}
          </h1>
          <span className="text-sm text-night/40">#{session.astrologer_id}</span>
          {session.priority !== null && (
            <span className="inline-flex items-center rounded-full bg-clay-100 px-2.5 py-1 text-xs font-medium text-clay-700">
              P{session.priority}
            </span>
          )}
        </div>
        <p className="text-sm text-night/50">
          {session.resolved_by === null
            ? "Still active"
            : session.resolved_by === "bot"
              ? "Resolved by the bot"
              : `Escalated to ticket #${session.ticket_id}`}
          {session.category && ` · ${session.category.replace(/_/g, " ")}`}
        </p>
      </div>

      <div className="flex flex-col gap-3 rounded-2xl bg-white p-4 shadow-sm">
        {session.messages.length === 0 ? (
          <p className="text-sm text-night/40">
            No transcript available for this conversation — it started before message logging was
            added.
          </p>
        ) : (
          session.messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === "astrologer" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-md rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                  message.role === "astrologer"
                    ? "bg-terracotta text-white"
                    : "border border-night/10 bg-cream text-ink"
                }`}
              >
                {message.text}
                <p
                  className={`mt-1 text-xs ${
                    message.role === "astrologer" ? "text-white/70" : "text-night/40"
                  }`}
                >
                  {new Date(message.created_at).toLocaleTimeString(undefined, {
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
