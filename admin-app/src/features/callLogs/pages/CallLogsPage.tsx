import { useSearchParams } from "react-router-dom";

import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useCallLogs } from "../api/useCallLogs";
import { CallLogFilters } from "../components/CallLogFilters";
import { CallLogsTable } from "../components/CallLogsTable";

export function CallLogsPage() {
  const [searchParams] = useSearchParams();
  const resolutionStatus = searchParams.get("resolution_status") ?? undefined;
  const dateFrom = searchParams.get("from") ?? undefined;
  const dateTo = searchParams.get("to") ?? undefined;
  const astrologer = searchParams.get("astrologer") ?? undefined;

  const { data: calls, status } = useCallLogs({ resolutionStatus, dateFrom, dateTo, astrologer });

  const activeCalls = calls?.filter((c) => c.status !== "ended" && c.status !== "failed") ?? [];
  const completedCalls = calls?.filter((c) => c.status === "ended" || c.status === "failed") ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-night">AI Call Logs</h1>
          <p className="text-sm text-night/50">
            Every AI phone call with astrologers — what was discussed, whether the issue was
            resolved, and what to do next.
          </p>
        </div>
        <CallLogFilters />
      </div>

      {status === "pending" && <Spinner label="Loading call logs…" />}
      {status === "error" && <EmptyState title="Couldn't load call logs" />}
      {status === "success" && calls.length === 0 && (
        <EmptyState title="No AI calls yet" />
      )}
      {status === "success" && calls.length > 0 && (
        <>
          {activeCalls.length > 0 && (
            <div>
              <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-night/40">
                Active ({activeCalls.length})
              </h2>
              <CallLogsTable calls={activeCalls} />
            </div>
          )}

          <div className="flex flex-col gap-2">
            <h2 className="text-sm font-medium uppercase tracking-wide text-night/40">
              Completed ({completedCalls.length})
            </h2>
            {completedCalls.length === 0 ? (
              <p className="text-sm text-night/40">No completed calls yet.</p>
            ) : (
              <CallLogsTable calls={completedCalls} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
