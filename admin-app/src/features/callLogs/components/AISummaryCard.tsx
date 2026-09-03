import type { ResolutionStatus } from "@astrohelp/shared";

interface Props {
  summary: string | null;
  suggestedSolution: string | null;
  nextAction: string | null;
  resolutionStatus: ResolutionStatus | null;
}

const OUTCOME_CONFIG: Record<ResolutionStatus, { label: string; bg: string; border: string; text: string }> = {
  resolved: { label: "Issue Resolved", bg: "bg-moss-100", border: "border-moss/30", text: "text-moss-700" },
  follow_up_required: { label: "Follow-up Required", bg: "bg-ochre-100", border: "border-ochre/30", text: "text-ochre-700" },
  escalated: { label: "Escalated to Human", bg: "bg-clay-100", border: "border-clay/30", text: "text-clay-700" },
  unknown: { label: "Outcome Unknown", bg: "bg-slate-100", border: "border-slate-300", text: "text-slate-600" },
  not_connected: { label: "Call Not Connected", bg: "bg-slate-100", border: "border-slate-300", text: "text-slate-600" },
};

export function AISummaryCard({ summary, suggestedSolution, nextAction, resolutionStatus }: Props) {
  const hasContent = summary || suggestedSolution || nextAction;

  if (!hasContent) {
    return (
      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-night">AI Summary</h2>
        <p className="mt-2 text-sm text-night/40">No AI summary generated yet.</p>
      </div>
    );
  }

  const outcome = resolutionStatus ? OUTCOME_CONFIG[resolutionStatus] : null;

  return (
    <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
      {outcome && (
        <div className={`${outcome.bg} border-b ${outcome.border} px-5 py-3`}>
          <p className={`text-sm font-semibold ${outcome.text}`}>{outcome.label}</p>
        </div>
      )}

      <div className="flex flex-col gap-5 p-5">
        {summary && (
          <div>
            <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-night/40">
              What happened
            </p>
            <p className="text-sm leading-relaxed text-ink">{summary}</p>
          </div>
        )}

        {(suggestedSolution || nextAction) && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {suggestedSolution && (
              <div className="rounded-xl border border-moss/15 bg-moss-100/50 px-4 py-3">
                <p className="mb-1 text-xs font-semibold text-moss-700">Suggested Solution</p>
                <p className="text-sm leading-relaxed text-night/80">{suggestedSolution}</p>
              </div>
            )}
            {nextAction && (
              <div className="rounded-xl border border-ochre/15 bg-ochre-100/50 px-4 py-3">
                <p className="mb-1 text-xs font-semibold text-ochre-700">Next Action</p>
                <p className="text-sm leading-relaxed text-night/80">{nextAction}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
