import { useSearchParams } from "react-router-dom";

// Two plain date inputs writing directly to the "from"/"to" URL params —
// same self-contained useSearchParams convention as TicketFilters' status/
// assigned_admin_id selects, so this drops into any page's filter row with
// no extra prop plumbing. Equal from/to values mean "just this one day";
// either can be set alone for an open-ended range.
export function DateRangeFilter() {
  const [searchParams, setSearchParams] = useSearchParams();
  const from = searchParams.get("from") ?? "";
  const to = searchParams.get("to") ?? "";

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  }

  function clear() {
    const next = new URLSearchParams(searchParams);
    next.delete("from");
    next.delete("to");
    setSearchParams(next);
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="flex items-center gap-1.5 text-sm text-night/60">
        From
        <input
          type="date"
          value={from}
          max={to || undefined}
          onChange={(e) => updateParam("from", e.target.value)}
          className="rounded-lg border border-night/15 px-2 py-[7px] text-sm text-ink focus-visible:border-terracotta"
        />
      </label>
      <label className="flex items-center gap-1.5 text-sm text-night/60">
        To
        <input
          type="date"
          value={to}
          min={from || undefined}
          onChange={(e) => updateParam("to", e.target.value)}
          className="rounded-lg border border-night/15 px-2 py-[7px] text-sm text-ink focus-visible:border-terracotta"
        />
      </label>
      {(from || to) && (
        <button
          type="button"
          onClick={clear}
          className="text-sm font-medium text-night/40 underline decoration-night/20 hover:text-night/60"
        >
          Clear dates
        </button>
      )}
    </div>
  );
}
