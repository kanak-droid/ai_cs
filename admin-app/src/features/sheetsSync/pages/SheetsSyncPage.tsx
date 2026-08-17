import { Button } from "../../../components/Button";
import { useSyncSheets } from "../api/useSyncSheets";

const TABLE_LABELS: Record<string, string> = {
  roster: "Astrologer roster",
  kyc: "KYC records",
  payout_status: "Payout status (current cycle, incl. KYC/TDS)",
  expert_priority: "Priority ranking",
  provisioned_astrologers: "Newly provisioned astrologers",
  astrologer_profiles: "Linked astrologer phone",
};

export function SheetsSyncPage() {
  const sync = useSyncSheets();

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-semibold text-night">Sheets Sync</h1>
        <p className="text-sm text-night/50">
          Pulls the latest roster, KYC, payout (incl. KYC/TDS per cycle), and priority-ranking data
          from the ops team's Google Sheets and analytics query into the database the chatbot reads
          from. Runs automatically once a day — use this after editing a source to refresh sooner.
        </p>
      </div>

      <div>
        <Button onClick={() => sync.mutate()} disabled={sync.isPending}>
          {sync.isPending ? "Syncing…" : "Sync now"}
        </Button>
      </div>

      {sync.isError && (
        <p className="text-sm text-clay">
          Sync failed to run at all — check the backend has the Google service account
          credentials configured.
        </p>
      )}

      {sync.isSuccess && (
        <div className="rounded-xl border border-night/10 bg-white p-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-night/40">
            Last sync result
          </p>
          <ul className="flex flex-col gap-1 text-sm">
            {Object.entries(sync.data).map(([key, value]) => (
              <li key={key} className="flex items-center justify-between gap-3">
                <span className="text-night/70">{TABLE_LABELS[key] ?? key}</span>
                <span className={value === "error" ? "font-medium text-clay" : "font-medium text-night"}>
                  {value === "error" ? "Failed — see backend logs" : `${value} rows`}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
