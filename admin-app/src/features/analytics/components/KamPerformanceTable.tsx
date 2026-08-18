import type { KamPerformance } from "@astrohelp/shared";

function formatTat(hours: number | null): string {
  if (hours === null) return "—";
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

export function KamPerformanceTable({ rows }: { rows: KamPerformance[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-night/40">No KAMs/CS admins to show yet.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
            <th className="px-4 py-3 font-medium">Name</th>
            <th className="px-4 py-3 font-medium">Role</th>
            <th className="px-4 py-3 font-medium">Pending</th>
            <th className="px-4 py-3 font-medium">Assigned</th>
            <th className="px-4 py-3 font-medium">Solved</th>
            <th className="px-4 py-3 font-medium">Avg. TAT</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.admin_id} className="border-b border-night/5 last:border-0">
              <td className="px-4 py-3 font-medium text-night">{row.name}</td>
              <td className="px-4 py-3 uppercase text-night/60">{row.role}</td>
              <td className="px-4 py-3 text-night">{row.pending_count}</td>
              <td className="px-4 py-3 text-night">{row.assigned_count}</td>
              <td className="px-4 py-3 text-night">{row.solved_count}</td>
              <td className="px-4 py-3 text-night">{formatTat(row.avg_tat_hours)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
