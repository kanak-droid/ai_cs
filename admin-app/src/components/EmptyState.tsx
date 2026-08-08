import type { ReactNode } from "react";

export function EmptyState({ title, description }: { title: string; description?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 px-6 py-16 text-center">
      <p className="text-sm font-medium text-night">{title}</p>
      {description ? <p className="max-w-sm text-sm text-night/50">{description}</p> : null}
    </div>
  );
}
