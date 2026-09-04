import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { CallStatusBadge } from "../../callLogs/components/CallStatusBadge";
import { TranscriptCard } from "../../callLogs/components/TranscriptCard";
import { fetchFeedbackCallDetail } from "../api/feedbackCallsApi";

function formatDuration(createdAt: string, endedAt: string | null): string {
  if (!endedAt) return "In progress";
  const seconds = Math.round((new Date(endedAt).getTime() - new Date(createdAt).getTime()) / 1000);
  if (seconds < 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function RatingStars({ rating }: { rating: number | null }) {
  if (rating == null) return <span className="text-sm text-night/30">No rating</span>;
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={`text-lg ${i < rating ? "text-ochre" : "text-night/15"}`}>
          ★
        </span>
      ))}
      <span className="ml-1 text-sm font-medium text-night">{rating}/5</span>
    </div>
  );
}

function FeedbackInsightsCard({ nextAction, summary }: { nextAction: string | null; summary: string | null }) {
  let data: {
    app_rating?: number | null;
    topics_discussed?: string[];
    positive_feedback?: string[];
    negative_feedback?: string[];
  } = {};
  try {
    if (nextAction) data = JSON.parse(nextAction);
  } catch {
    // fall through
  }

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold text-night">Feedback Insights</h2>

      {summary && (
        <div className="mb-4">
          <p className="text-sm text-night/70">{summary}</p>
        </div>
      )}

      <div className="mb-4">
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-night/40">App Rating</p>
        <RatingStars rating={data.app_rating ?? null} />
      </div>

      {(data.topics_discussed ?? []).length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-night/40">Topics Discussed</p>
          <div className="flex flex-wrap gap-2">
            {data.topics_discussed!.map((t) => (
              <span key={t} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                {t.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>
      )}

      {(data.positive_feedback ?? []).length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-moss-600">Positive</p>
          <ul className="space-y-1">
            {data.positive_feedback!.map((f, i) => (
              <li key={i} className="text-sm text-night/70">+ {f}</li>
            ))}
          </ul>
        </div>
      )}

      {(data.negative_feedback ?? []).length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-clay-600">Needs Improvement</p>
          <ul className="space-y-1">
            {data.negative_feedback!.map((f, i) => (
              <li key={i} className="text-sm text-night/70">- {f}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function FeedbackCallDetailPage() {
  const { id } = useParams<{ id: string }>();
  const callId = Number(id);
  const { data: call, status } = useQuery({
    queryKey: ["admin", "feedback-call-detail", callId],
    queryFn: () => fetchFeedbackCallDetail(callId),
  });

  if (status === "pending") return <Spinner label="Loading feedback call..." />;
  if (status === "error" || !call) return <EmptyState title="Couldn't load this call" />;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link to="/feedback-calls" className="text-sm text-night/50 hover:text-night">
          ← Back to Feedback Calls
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="font-display text-2xl font-semibold text-night">
            {call.astrologer_name}
          </h1>
          <span className="text-sm text-night/40">#{call.astrologer_id}</span>
          <CallStatusBadge status={call.status} />
        </div>
        <p className="mt-1 text-sm text-night/50">
          Feedback Call #{call.id} · {new Date(call.created_at).toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <FeedbackInsightsCard nextAction={call.next_action} summary={call.support_summary} />
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
                <dt className="text-night/40">Duration</dt>
                <dd className="text-night">{formatDuration(call.created_at, call.ended_at)}</dd>
              </div>
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

          {call.suggested_solution && (
            <div className="rounded-2xl bg-white p-4 shadow-sm">
              <h2 className="mb-3 text-sm font-semibold text-night">Key Suggestion</h2>
              <p className="text-sm text-night/70">{call.suggested_solution}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
