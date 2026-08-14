import { useAdminsLookup } from "../api/useAdminsLookup";

export function AssignedToCard({
  assignedAdminId,
  assignedCsId,
  kamNotified,
  csNotified,
}: {
  assignedAdminId: number | null;
  assignedCsId: number | null;
  kamNotified: boolean;
  csNotified: boolean;
}) {
  const { data: admins } = useAdminsLookup();
  const kam = admins?.find((a) => a.id === assignedAdminId);
  const cs = admins?.find((a) => a.id === assignedCsId);

  if (!kam && !cs) return null;

  return (
    <div className="rounded-xl border border-night/10 p-4">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-night/40">Assigned to</p>
      {kam && (
        <p className="text-sm text-night">
          <span className="text-night/50">KAM:</span> {kam.name}
          {!kamNotified && (
            <span className="text-xs text-night/40"> (their regular contact — not notified on this one)</span>
          )}
        </p>
      )}
      {cs && (
        <p className="text-sm text-night">
          <span className="text-night/50">CS:</span> {cs.name}
          {cs.languages.length > 0 && (
            <span className="text-xs text-night/40"> ({cs.languages.join("/")})</span>
          )}
          {!csNotified && <span className="text-xs text-night/40"> (not notified on this one)</span>}
        </p>
      )}
    </div>
  );
}
