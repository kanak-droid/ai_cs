import { Link, useParams } from "react-router-dom";

import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useCallLogDetail } from "../api/useCallLogDetail";
import { AISummaryCard } from "../components/AISummaryCard";
import { CallStatusBadge } from "../components/CallStatusBadge";
import { ResolutionStatusBadge } from "../components/ResolutionStatusBadge";
import { TranscriptCard } from "../components/TranscriptCard";

function PriorityBadge({ priority }: { priority: number | null }) {
  if (priority === null) return null;
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

function formatTriggeredBy(triggeredBy: string): string {
  if (triggeredBy === "user_request") return "User request";
  if (triggeredBy.startsWith("admin:")) {
    const parts = triggeredBy.split(":");
    return `Admin: ${parts[1] ?? "unknown"}${parts[2] ? ` (${parts[2]})` : ""}`;
  }
  return triggeredBy;
}

export function CallLogDetailPage() {
  const { id } = useParams<{ id: string }>();
  const callId = Number(id);
  const { data: call, status } = useCallLogDetail(callId);

  if (status === "pending") return <Spinner label="Loading call…" />;
  if (status === "error" || !call) return <EmptyState title="Couldn't load this call" />;

  const ticketId = call.ticket_id ?? call.created_ticket_id;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link to="/call-logs" className="text-sm text-night/50 hover:text-night">
          ← Back to AI Call Logs
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="font-display text-2xl font-semibold text-night">
            {call.astrologer_name}
          </h1>
          <span className="text-sm text-night/40">#{call.astrologer_id}</span>
          <PriorityBadge priority={call.priority} />
          <CallStatusBadge status={call.status} />
          <ResolutionStatusBadge status={call.resolution_status} />
        </div>
        <p className="mt-1 text-sm text-night/50">
          Call #{call.id} · {new Date(call.created_at).toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <AISummaryCard
            summary={call.support_summary}
            suggestedSolution={call.suggested_solution}
            nextAction={call.next_action}
            resolutionStatus={call.resolution_status}
          />
          <TranscriptCard transcript={call.transcript} />
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-2xl bg-white p-4 shadow-sm">
            <h2 className="mb-3 text-sm font-semibold text-night">Call Details</h2>
            <dl className="flex flex-col gap-2 text-sm">
              <div>
                <dt className="text-night/40">Phone</dt>
                <dd className="font-medium text-night">{call.phone_number}</dd>
              </div>
              <div>
                <dt className="text-night/40">Triggered by</dt>
                <dd className="text-night">{formatTriggeredBy(call.triggered_by)}</dd>
              </div>
              <div>
                <dt className="text-night/40">Duration</dt>
                <dd className="text-night">{formatDuration(call.created_at, call.ended_at)}</dd>
              </div>
              {call.ended_reason && (
                <div>
                  <dt className="text-night/40">Ended reason</dt>
                  <dd className="text-night">{call.ended_reason}</dd>
                </div>
              )}
              <div>
                <dt className="text-night/40">Started</dt>
                <dd className="text-night">{new Date(call.created_at).toLocaleString()}</dd>
              </div>
              {call.ended_at && (
                <div>
                  <dt className="text-night/40">Ended</dt>
                  <dd className="text-night">{new Date(call.ended_at).toLocaleString()}</dd>
                </div>
              )}
            </dl>
          </div>

          {ticketId && (
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <h2 className="mb-3 text-sm font-semibold text-night">Linked Ticket</h2>
              <Link
                to={`/tickets/${ticketId}`}
                className="font-medium text-terracotta hover:underline"
              >
                Ticket #{ticketId} →
              </Link>
              {call.ticket_id && call.created_ticket_id && call.ticket_id !== call.created_ticket_id && (
                <p className="mt-2 text-xs text-night/40">
                  Originated from ticket #{call.ticket_id}, AI created ticket #{call.created_ticket_id}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
