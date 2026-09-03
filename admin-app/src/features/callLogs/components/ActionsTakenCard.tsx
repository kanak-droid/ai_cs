import type { ActionTaken } from "@astrohelp/shared";

export function ActionsTakenCard({ actions }: { actions: ActionTaken[] | null }) {
  const items = actions ?? [];

  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-night">Actions Taken</h2>
      {items.length === 0 ? (
        <p className="text-sm text-night/40">No tool actions were taken during this call.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((action, i) => (
            <li key={i} className="flex items-start gap-2.5 text-sm">
              <span className={`mt-0.5 shrink-0 ${action.ok ? "text-moss" : "text-clay"}`}>
                {action.ok ? "✓" : "✗"}
              </span>
              <div className="min-w-0">
                <span className="font-mono text-xs text-night/60">{action.tool}</span>
                {action.summary && (
                  <p className="mt-0.5 text-night/70">{action.summary}</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
