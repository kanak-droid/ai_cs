import type { CallStatus } from "@astrohelp/shared";

const CONFIG: Record<CallStatus, { label: string; classes: string }> = {
  queued: { label: "Queued", classes: "bg-slate-100 text-slate-600" },
  ringing: { label: "Ringing", classes: "bg-ochre-100 text-ochre-700" },
  in_progress: { label: "In Progress", classes: "bg-terracotta-100 text-terracotta-700" },
  ended: { label: "Ended", classes: "bg-slate-100 text-slate-600" },
  failed: { label: "Failed", classes: "bg-clay-100 text-clay-700" },
};

export function CallStatusBadge({ status }: { status: CallStatus }) {
  const { label, classes } = CONFIG[status] ?? CONFIG.ended;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${classes}`}
    >
      {label}
    </span>
  );
}
