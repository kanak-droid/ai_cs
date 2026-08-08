import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useSlackLog } from "../api/useSlackLog";
import { SlackLogTable } from "../components/SlackLogTable";

export function SlackLogPage() {
  const { data: entries, status } = useSlackLog();

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-night">Slack Log</h1>
        <p className="text-sm text-night/50">
          Real Slack isn't wired up yet — this is a visual record of every notification that
          would have been sent.
        </p>
      </div>

      {status === "pending" && <Spinner label="Loading log…" />}
      {status === "error" && <EmptyState title="Couldn't load the Slack log" />}
      {status === "success" && entries.length === 0 && (
        <EmptyState title="No notifications yet" />
      )}
      {status === "success" && entries.length > 0 && <SlackLogTable entries={entries} />}
    </div>
  );
}
