import type { PriorityFilter } from "@astrohelp/shared";
import { useSearchParams } from "react-router-dom";

import { DateRangeFilter } from "../../../components/DateRangeFilter";
import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useAnalytics } from "../api/useAnalytics";
import { KamPerformanceTable } from "../components/KamPerformanceTable";
import { StatCard } from "../components/StatCard";
import { TicketTrendChart } from "../components/TicketTrendChart";
import { TopCategoriesList } from "../components/TopCategoriesList";

const PRIORITY_OPTIONS: { value: PriorityFilter | ""; label: string }[] = [
  { value: "", label: "All priorities" },
  { value: "1", label: "P1" },
  { value: "2", label: "P2" },
  { value: "3", label: "P3" },
  { value: "4", label: "P4" },
  { value: "5", label: "P5" },
  { value: "unranked", label: "Unranked" },
];

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
  const [searchParams, setSearchParams] = useSearchParams();
  const priority = (searchParams.get("priority") as PriorityFilter | null) ?? undefined;
  const dateFrom = searchParams.get("from") ?? undefined;
  const dateTo = searchParams.get("to") ?? undefined;
  const { data: overview, status } = useAnalytics(priority, dateFrom, dateTo);

  if (status === "pending") return <Spinner label="Loading analytics…" />;
  if (status === "error" || !overview) return <EmptyState title="Couldn't load analytics" />;

  const totalResolved = overview.bot_resolved_count + overview.escalated_count;
  const botSharePct = totalResolved > 0 ? Math.round((overview.bot_resolved_count / totalResolved) * 100) : 0;
  const totalSatisfaction = overview.satisfied_count + overview.unsatisfied_count;
  const satisfiedPct =
    totalSatisfaction > 0 ? Math.round((overview.satisfied_count / totalSatisfaction) * 100) : null;
  const totalRatings = Object.values(overview.rating_distribution).reduce((sum, n) => sum + n, 0);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-night">Analytics</h1>
          <p className="text-sm text-night/50">
            How AstroHelp is doing across every conversation, not just tickets.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={priority ?? ""}
            onChange={(e) => {
              const next = new URLSearchParams(searchParams);
              if (e.target.value) {
                next.set("priority", e.target.value);
              } else {
                next.delete("priority");
              }
              setSearchParams(next);
            }}
            className="rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
          >
            {PRIORITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <DateRangeFilter />
        </div>
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
          hint={`out of 5 stars${totalRatings > 0 ? ` · ${totalRatings} rating${totalRatings === 1 ? "" : "s"}` : " · no ratings yet"}`}
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TicketTrendChart title="Week by week" data={overview.weekly_ticket_trend} granularity="week" />
        <TicketTrendChart title="Month by month" data={overview.monthly_ticket_trend} granularity="month" />
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-night">Most common issues</h2>
        <TopCategoriesList categories={overview.top_categories} />
      </div>

      <div>
        <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-night/40">
          KAM / CS performance
        </h2>
        <KamPerformanceTable rows={overview.kam_performance} />
      </div>
    </div>
  );
}
