import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useEmailLog } from "../api/useEmailLog";
import { EmailLogTable } from "../components/EmailLogTable";

export function EmailLogPage() {
  const { data: entries, status } = useEmailLog();

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-semibold text-night">Email Log</h1>
        <p className="text-sm text-night/50">
          Real email isn't wired up yet — this is a visual record of every email that would have
          been sent, including admin signup password-set links.
        </p>
      </div>

      {status === "pending" && <Spinner label="Loading log…" />}
      {status === "error" && <EmptyState title="Couldn't load the email log" />}
      {status === "success" && entries.length === 0 && (
        <EmptyState title="No emails yet" />
      )}
      {status === "success" && entries.length > 0 && <EmailLogTable entries={entries} />}
    </div>
  );
}
