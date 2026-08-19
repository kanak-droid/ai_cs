import type { TicketPeriodCount } from "@astrohelp/shared";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// night/50 and night's own hex (see tailwind-preset.js) — recharts takes raw
// SVG color strings, not Tailwind classes, so the design tokens are
// duplicated here rather than imported.
const AXIS_COLOR = "rgba(32, 28, 24, 0.5)";
const GRID_COLOR = "rgba(32, 28, 24, 0.08)";
const CREATED_COLOR = "#DC5F2A"; // terracotta
const RESOLVED_COLOR = "#5C7A5A"; // moss

function formatPeriodLabel(period: string, granularity: "week" | "month"): string {
  const parsed = new Date(`${period}T00:00:00`);
  return granularity === "month"
    ? parsed.toLocaleDateString("en-IN", { month: "short", year: "2-digit" })
    : parsed.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function TicketTrendChart({
  title,
  data,
  granularity,
}: {
  title: string;
  data: TicketPeriodCount[];
  granularity: "week" | "month";
}) {
  const chartData = data.map((row) => ({ ...row, label: formatPeriodLabel(row.period, granularity) }));

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-night">{title}</h2>
      {chartData.length === 0 ? (
        <p className="text-sm text-night/40">No tickets in this range yet.</p>
      ) : (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={GRID_COLOR} />
              <XAxis dataKey="label" tick={{ fontSize: 12, fill: AXIS_COLOR }} axisLine={{ stroke: GRID_COLOR }} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: AXIS_COLOR }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 10, border: "1px solid rgba(32,28,24,0.1)", fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="created_count" name="Raised" fill={CREATED_COLOR} radius={[4, 4, 0, 0]} />
              <Bar dataKey="resolved_count" name="Resolved" fill={RESOLVED_COLOR} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
