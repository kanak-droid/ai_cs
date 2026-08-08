export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8 text-night/60" role="status">
      <div
        className="h-6 w-6 animate-spin rounded-full border-2 border-terracotta/30 border-t-terracotta motion-reduce:animate-none"
        aria-hidden="true"
      />
      {label ? <p className="text-sm">{label}</p> : null}
    </div>
  );
}
