import { STATUS_LABELS, type TicketStatus } from "@astrohelp/shared";
import { useSearchParams } from "react-router-dom";

import { useAuth } from "../../../auth/AuthContext";
import { DateRangeFilter } from "../../../components/DateRangeFilter";
import { useAdminsLookup } from "../api/useAdminsLookup";

// All queryable statuses for the FILTER dropdown — deliberately not just
// ADMIN_SETTABLE_STATUSES, which now excludes "closed" (an admin can't set
// it manually anymore, but tickets still reach it via astrologer
// confirmation/48h auto-close, and admins still need to filter for them).
const ALL_STATUSES: TicketStatus[] = [
  "submitted",
  "assigned_to_kam",
  "under_review",
  "in_progress",
  "resolved",
  "closed",
];

export function TicketFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: admins } = useAdminsLookup();
  const { admin } = useAuth();

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={searchParams.get("status") ?? ""}
        onChange={(e) => updateParam("status", e.target.value)}
        className="rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
      >
        <option value="">All statuses</option>
        {ALL_STATUSES.map((status) => (
          <option key={status} value={status}>
            {STATUS_LABELS[status]}
          </option>
        ))}
      </select>

      <select
        value={searchParams.get("assigned_admin_id") ?? (admin ? String(admin.adminId) : "all")}
        onChange={(e) => updateParam("assigned_admin_id", e.target.value)}
        className="rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
      >
        <option value="all">All admins</option>
        {admins?.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name} ({a.role.toUpperCase()}){a.id === admin?.adminId ? " — me" : ""}
          </option>
        ))}
      </select>

      <DateRangeFilter />
    </div>
  );
}
