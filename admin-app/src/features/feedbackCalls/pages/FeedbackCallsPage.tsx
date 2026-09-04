import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { DateRangeFilter } from "../../../components/DateRangeFilter";
import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { CallStatusBadge } from "../../callLogs/components/CallStatusBadge";
import { searchAstrologers, triggerFeedbackCall } from "../api/feedbackCallsApi";
import { useFeedbackCalls } from "../api/useFeedbackCalls";

import type { Astrologer, CallLogSummary } from "@astrohelp/shared";

function formatDuration(createdAt: string, endedAt: string | null): string {
  if (!endedAt) return "In progress";
  const seconds = Math.round((new Date(endedAt).getTime() - new Date(createdAt).getTime()) / 1000);
  if (seconds < 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

function FeedbackInsights({ nextAction }: { nextAction: string | null }) {
  if (!nextAction) return null;
  try {
    const data = JSON.parse(nextAction);
    return (
      <div className="flex flex-wrap gap-2">
        {data.app_rating != null && (
          <span className="rounded-full bg-terracotta/10 px-2.5 py-0.5 text-xs font-medium text-terracotta">
            Rating: {data.app_rating}/5
          </span>
        )}
        {(data.topics_discussed ?? []).map((t: string) => (
          <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
            {t.replace(/_/g, " ")}
          </span>
        ))}
      </div>
    );
  } catch {
    return null;
  }
}

function TriggerCallButton() {
  const [query, setQuery] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const queryClient = useQueryClient();

  const { data: results } = useQuery({
    queryKey: ["admin", "astrologer-search", query],
    queryFn: () => searchAstrologers(query),
    enabled: query.length >= 1,
    staleTime: 10_000,
  });

  const mutation = useMutation({
    mutationFn: triggerFeedbackCall,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "feedback-calls"] });
      setQuery("");
      setShowDropdown(false);
    },
  });

  return (
    <div className="relative">
      <input
        type="text"
        placeholder="Trigger feedback call..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setShowDropdown(true);
        }}
        onFocus={() => setShowDropdown(true)}
        className="w-56 rounded-lg border border-night/15 px-3 py-2 text-sm text-ink placeholder:text-night/30 focus-visible:border-terracotta focus-visible:outline-none"
      />
      {showDropdown && query && results && results.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-48 overflow-auto rounded-xl border border-night/10 bg-white shadow-lg">
          {results.map((a: Astrologer) => (
            <button
              key={a.id}
              type="button"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate(a.id)}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm hover:bg-cream/60 disabled:opacity-50"
            >
              <span className="font-medium text-night">{a.name}</span>
              <span className="text-night/40">#{a.id}</span>
              <span className="ml-auto text-xs text-terracotta">Call</span>
            </button>
          ))}
        </div>
      )}
      {mutation.isSuccess && (
        <p className="mt-1 text-xs text-moss-600">Call triggered!</p>
      )}
      {mutation.isError && (
        <p className="mt-1 text-xs text-clay-600">Failed to trigger call</p>
      )}
    </div>
  );
}

export function FeedbackCallsPage() {
  const [searchParams] = useSearchParams();
  const dateFrom = searchParams.get("from") ?? undefined;
  const dateTo = searchParams.get("to") ?? undefined;
  const astrologer = searchParams.get("astrologer") ?? undefined;
  const navigate = useNavigate();

  const { data: calls, status } = useFeedbackCalls({ dateFrom, dateTo, astrologer });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-night">Feedback Calls</h1>
          <p className="text-sm text-night/50">
            AI-powered feedback calls to understand astrologers' app experience.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <TriggerCallButton />
          <DateRangeFilter />
        </div>
      </div>

      {status === "pending" && <Spinner label="Loading feedback calls..." />}
      {status === "error" && <EmptyState title="Couldn't load feedback calls" />}
      {status === "success" && calls.length === 0 && (
        <EmptyState
          title="No feedback calls yet"
          description="Use the search box above to trigger a feedback call to an astrologer."
        />
      )}
      {status === "success" && calls.length > 0 && (
        <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
                <th className="px-4 py-3 font-medium">Astrologer</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Summary</th>
                <th className="px-4 py-3 font-medium">Insights</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((c: CallLogSummary) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/feedback-calls/${c.id}`)}
                  className="cursor-pointer border-b border-night/5 last:border-0 hover:bg-cream/60"
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-night">{c.astrologer_name}</p>
                    <p className="text-xs text-night/40">#{c.astrologer_id}</p>
                  </td>
                  <td className="px-4 py-3">
                    <CallStatusBadge status={c.status} />
                  </td>
                  <td className="max-w-xs px-4 py-3 text-night/70 truncate">
                    {c.support_summary ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <FeedbackInsights nextAction={null} />
                  </td>
                  <td className="px-4 py-3 text-night/60">
                    {formatDuration(c.created_at, c.ended_at)}
                  </td>
                  <td className="px-4 py-3 text-xs text-night/50">
                    {new Date(c.created_at).toLocaleString(undefined, {
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
      )}
    </div>
  );
}
