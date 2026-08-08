export function DescriptionPanel({
  description,
  descriptionEn,
  language,
}: {
  description: string;
  descriptionEn: string;
  language: string;
}) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div className="rounded-xl border border-night/10 p-4">
        <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-night/40">
          Original ({language})
        </p>
        <p className="whitespace-pre-wrap text-sm text-ink">{description}</p>
      </div>
      <div className="rounded-xl border border-night/10 bg-terracotta-100 p-4">
        <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-terracotta-700">
          English summary
        </p>
        <p className="whitespace-pre-wrap text-sm text-ink">{descriptionEn}</p>
      </div>
    </div>
  );
}
