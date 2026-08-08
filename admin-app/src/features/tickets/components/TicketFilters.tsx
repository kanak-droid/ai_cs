import { ADMIN_SETTABLE_STATUSES, STATUS_LABELS, type TicketStatus } from "@astrohelp/shared";
import { useSearchParams } from "react-router-dom";

import { useAdminsLookup } from "../api/useAdminsLookup";

const ALL_STATUSES: TicketStatus[] = ["submitted", "assigned_to_kam", ...ADMIN_SETTABLE_STATUSES];

export function TicketFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: admins } = useAdminsLookup();

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
        className="rounded-lg border-night/15 text-sm text-ink focus-visible:border-terracotta"
      >
        <option value="">All statuses</option>
        {ALL_STATUSES.map((status) => (
          <option key={status} value={status}>
            {STATUS_LABELS[status]}
          </option>
        ))}
      </select>

      <select
        value={searchParams.get("assigned_admin_id") ?? ""}
        onChange={(e) => updateParam("assigned_admin_id", e.target.value)}
        className="rounded-lg border-night/15 text-sm text-ink focus-visible:border-terracotta"
      >
        <option value="">All admins</option>
        {admins?.map((admin) => (
          <option key={admin.id} value={admin.id}>
            {admin.name}
          </option>
        ))}
      </select>

      <select
        value={searchParams.get("sort") ?? "desc"}
        onChange={(e) => updateParam("sort", e.target.value)}
        className="rounded-lg border-night/15 text-sm text-ink focus-visible:border-terracotta"
      >
        <option value="desc">Newest first</option>
        <option value="asc">Oldest first</option>
      </select>
    </div>
  );
}
