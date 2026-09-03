import { useSearchParams } from "react-router-dom";

import { DateRangeFilter } from "../../../components/DateRangeFilter";

const RESOLUTION_OPTIONS = [
  { value: "", label: "All outcomes" },
  { value: "resolved", label: "Resolved" },
  { value: "follow_up_required", label: "Follow-up Required" },
  { value: "escalated", label: "Escalated" },
  { value: "unknown", label: "Unknown" },
  { value: "not_connected", label: "Not Connected" },
];

export function CallLogFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const resolution = searchParams.get("resolution_status") ?? "";

  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={resolution}
        onChange={(e) => {
          const next = new URLSearchParams(searchParams);
          if (e.target.value) {
            next.set("resolution_status", e.target.value);
          } else {
            next.delete("resolution_status");
          }
          setSearchParams(next);
        }}
        className="rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
      >
        {RESOLUTION_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <DateRangeFilter />
    </div>
  );
}
