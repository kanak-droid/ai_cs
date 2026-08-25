import { useState } from "react";

// Exactly 5 negative options per product decision — enough to cover the
// common complaints without turning this into a full form. Positive list
// isn't count-constrained, just kept short for the same reason.
const POSITIVE_REASONS = [
  "Quick response",
  "Issue fully resolved",
  "Clear communication",
  "Professional support",
];

const NEGATIVE_REASONS = [
  "My issue wasn't actually resolved",
  "It took too long to resolve",
  "The explanation wasn't clear",
  "I had to follow up multiple times",
  "Support wasn't helpful or polite",
];

export function TicketRatingWidget({
  ticketId,
  onSubmit,
}: {
  ticketId: number;
  onSubmit: (ticketId: number, rating: number, reasons: string[], comment: string | null) => void;
}) {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [reasons, setReasons] = useState<string[]>([]);
  const [comment, setComment] = useState("");

  function toggleReason(reason: string) {
    setReasons((prev) => (prev.includes(reason) ? prev.filter((r) => r !== reason) : [...prev, reason]));
  }

  // >=4 stars mirrors the backend's own satisfied/unsatisfied threshold
  // (see ticket_service.record_ticket_rating) — keep the two in sync.
  const reasonOptions = rating >= 4 ? POSITIVE_REASONS : NEGATIVE_REASONS;
  // A reason chip or a typed comment is always required, at every rating —
  // feedback with zero context (not even "what did you like") isn't useful
  // enough to accept on its own.
  const hasJustification = reasons.length > 0 || comment.trim().length > 0;
  const canSubmit = rating > 0 && hasJustification;

  return (
    <div className="rounded-2xl bg-white p-3 shadow-sm">
      <p className="mb-2 text-sm font-medium text-night">How was this resolution?</p>
      <div className="flex gap-1" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            aria-label={`${value} star${value > 1 ? "s" : ""}`}
            onClick={() => setRating(value)}
            onMouseEnter={() => setHovered(value)}
            onMouseLeave={() => setHovered(0)}
            className={`text-2xl leading-none ${
              value <= (hovered || rating) ? "text-ochre" : "text-night/20"
            }`}
          >
            ★
          </button>
        ))}
      </div>

      {rating > 0 && (
        <>
          <p className="mb-1.5 mt-3 text-xs font-medium text-night/60">
            {rating >= 4
              ? "What did you like? (pick one or tell us below)"
              : "What went wrong? (pick one or tell us below)"}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {reasonOptions.map((reason) => {
              const selected = reasons.includes(reason);
              return (
                <button
                  key={reason}
                  type="button"
                  onClick={() => toggleReason(reason)}
                  className={`rounded-full border px-2.5 py-1 text-xs ${
                    selected
                      ? "border-terracotta bg-terracotta/10 text-terracotta"
                      : "border-night/15 text-night/60"
                  }`}
                >
                  {reason}
                </button>
              );
            })}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={rating >= 4 ? "Tell us what you liked" : "Tell us what went wrong"}
            rows={2}
            className="mt-2 w-full resize-none rounded-lg border border-night/15 bg-cream px-3 py-2 text-sm text-ink placeholder:text-night/40 focus-visible:border-terracotta"
          />
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => onSubmit(ticketId, rating, reasons, comment.trim() || null)}
            className="mt-2 rounded-full bg-terracotta px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40"
          >
            Submit
          </button>
        </>
      )}
    </div>
  );
}
