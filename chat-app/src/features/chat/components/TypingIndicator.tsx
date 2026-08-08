export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 self-start rounded-2xl bg-white px-4 py-3 shadow-sm" aria-label="AstroHelp is typing">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-night/30 motion-safe:animate-bounce"
          style={{ animationDelay: `${i * 120}ms` }}
        />
      ))}
    </div>
  );
}
