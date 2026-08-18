const FAQS = [
  "When will my payout arrive?",
  "Why was my KYC rejected?",
  "Who is my point of contact?",
  "How do I change my profile photo?",
];

export function FaqChips({ onPick, disabled }: { onPick: (question: string) => void; disabled?: boolean }) {
  return (
    <div className="border-t border-night/10 bg-white px-3 pt-3">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-night/40">
        Common questions
      </p>
      <div className="flex flex-wrap gap-2 pb-1">
        {FAQS.map((question) => (
          <button
            key={question}
            type="button"
            disabled={disabled}
            onClick={() => onPick(question)}
            className="rounded-full border border-night/15 bg-cream px-3 py-1.5 text-sm text-night/70 transition-colors hover:border-terracotta hover:text-terracotta disabled:opacity-40"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
