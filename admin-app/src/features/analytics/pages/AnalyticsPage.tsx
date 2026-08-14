import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useAnalytics } from "../api/useAnalytics";
import { StatCard } from "../components/StatCard";
import { TopCategoriesList } from "../components/TopCategoriesList";

function formatSeconds(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.round(seconds / 60)}m`;
}

function formatHours(hours: number | null): string {
  if (hours === null) return "—";
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

export function AnalyticsPage() {
  const { data: overview, status } = useAnalytics();

  if (status === "pending") return <Spinner label="Loading analytics…" />;
  if (status === "error" || !overview) return <EmptyState title="Couldn't load analytics" />;

  const totalResolved = overview.bot_resolved_count + overview.escalated_count;
  const botSharePct = totalResolved > 0 ? Math.round((overview.bot_resolved_count / totalResolved) * 100) : 0;
  const totalSatisfaction = overview.satisfied_count + overview.unsatisfied_count;
  const satisfiedPct =
    totalSatisfaction > 0 ? Math.round((overview.satisfied_count / totalSatisfaction) * 100) : null;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-semibold text-night">Analytics</h1>
        <p className="text-sm text-night/50">
          How AstroHelp is doing across every conversation, not just tickets.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Resolved by bot"
          value={`${overview.bot_resolved_count}`}
          hint={totalResolved > 0 ? `${botSharePct}% of resolved conversations` : undefined}
        />
        <StatCard label="Escalated to a KAM" value={`${overview.escalated_count}`} />
        <StatCard
          label="Ticket satisfaction"
          value={satisfiedPct !== null ? `${satisfiedPct}%` : "—"}
          hint={
            totalSatisfaction > 0
              ? `${overview.satisfied_count} satisfied · ${overview.unsatisfied_count} not`
              : "No responses yet"
          }
        />
        <StatCard
          label="Avg. bot rating"
          value={overview.avg_bot_rating !== null ? overview.avg_bot_rating.toFixed(1) : "—"}
          hint="out of 5 stars"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <StatCard
          label="Avg. time to bot resolution"
          value={formatSeconds(overview.avg_bot_resolution_seconds)}
        />
        <StatCard
          label="Avg. ticket turnaround"
          value={formatHours(overview.avg_ticket_resolution_hours)}
          hint="Created to resolved"
        />
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-night">Most common issues</h2>
        <TopCategoriesList categories={overview.top_categories} />
      </div>
    </div>
  );
}
