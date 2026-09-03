import type { ResolutionStatus } from "@astrohelp/shared";

const CONFIG: Record<ResolutionStatus, { label: string; classes: string }> = {
  resolved: { label: "Resolved", classes: "bg-moss-100 text-moss-700" },
  follow_up_required: { label: "Follow-up Required", classes: "bg-ochre-100 text-ochre-700" },
  escalated: { label: "Escalated", classes: "bg-clay-100 text-clay-700" },
  unknown: { label: "Unknown", classes: "bg-slate-100 text-slate-600" },
  not_connected: { label: "Not Connected", classes: "bg-slate-100 text-slate-600" },
};

export function ResolutionStatusBadge({ status }: { status: ResolutionStatus | null }) {
  if (!status) return <span className="text-xs text-night/30">—</span>;
  const { label, classes } = CONFIG[status] ?? { label: status, classes: "bg-slate-100 text-slate-600" };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${classes}`}
    >
      {label}
    </span>
  );
}
