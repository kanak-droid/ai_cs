import type { CategoryCount } from "@astrohelp/shared";

export function TopCategoriesList({ categories }: { categories: CategoryCount[] }) {
  if (categories.length === 0) {
    return <p className="text-sm text-night/50">No categorized conversations yet.</p>;
  }
  const max = Math.max(...categories.map((c) => c.count));

  return (
    <div className="flex flex-col gap-2">
      {categories.map((c) => (
        <div key={c.category} className="flex items-center gap-3">
          <span className="w-32 shrink-0 truncate text-sm capitalize text-night">
            {c.category.replace(/_/g, " ")}
          </span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-cream">
            <div
              className="h-full rounded-full bg-terracotta"
              style={{ width: `${Math.max(6, (c.count / max) * 100)}%` }}
            />
          </div>
          <span className="w-8 shrink-0 text-right text-sm text-night/60">{c.count}</span>
        </div>
      ))}
    </div>
  );
}
