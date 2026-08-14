export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-night/40">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold text-night">{value}</p>
      {hint && <p className="mt-1 text-xs text-night/50">{hint}</p>}
    </div>
  );
}
