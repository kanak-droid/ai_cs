import { STATUS_COLOR_TOKEN, STATUS_LABELS, type TicketStatus } from "@astrohelp/shared";

const COLOR_CLASSES: Record<string, string> = {
  terracotta: "bg-terracotta-100 text-terracotta-700",
  ochre: "bg-ochre-100 text-ochre-700",
  moss: "bg-moss-100 text-moss-700",
  clay: "bg-clay-100 text-clay-700",
  slate: "bg-slate-100 text-slate-600",
};

export function TicketStatusBadge({ status }: { status: TicketStatus }) {
  const colorClass = COLOR_CLASSES[STATUS_COLOR_TOKEN[status]];
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${colorClass}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}
