import { useState } from "react";

// Same preset-chips-plus-free-text pattern as TicketRatingWidget, just for
// the bot conversation itself rather than a ticket's resolution — kept as
// its own list since "liked the chat" and "liked how the ticket was
// resolved" call for different wording.
const POSITIVE_REASONS = [
  "Quick response",
  "Clear and easy to understand",
  "Solved my problem",
  "Friendly and polite",
];

const NEGATIVE_REASONS = [
  "Didn't understand my question",
  "Answer wasn't clear",
  "Took too long / too many messages",
  "Felt robotic",
  "Didn't solve my problem",
];

export function FeedbackWidget({
  onSubmit,
}: {
  onSubmit: (rating: number, reasons: string[], comment: string) => void;
}) {
  const [rating, setRating] = useState(0);
  const [reasons, setReasons] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [hovered, setHovered] = useState(0);

  function toggleReason(reason: string) {
    setReasons((prev) => (prev.includes(reason) ? prev.filter((r) => r !== reason) : [...prev, reason]));
  }

  // >=4 stars mirrors TicketRatingWidget/the backend's satisfied threshold.
  const reasonOptions = rating >= 4 ? POSITIVE_REASONS : NEGATIVE_REASONS;
  // A reason chip or a typed comment is always required, at every rating —
  // feedback with zero context (not even "what did you like") isn't useful
  // enough to accept on its own.
  const hasJustification = reasons.length > 0 || comment.trim().length > 0;
  const canSubmit = rating > 0 && hasJustification;

  return (
    <div className="mt-2 max-w-[80%] rounded-2xl bg-white p-3 shadow-sm">
      <p className="mb-2 text-sm font-medium text-night">How was this?</p>
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
              : "What could be better? (pick one or tell us below)"}
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
            placeholder={rating >= 4 ? "Tell us what you liked" : "Tell us what could be better"}
            rows={2}
            className="mt-2 w-full resize-none rounded-lg border border-night/15 bg-cream px-3 py-2 text-sm text-ink placeholder:text-night/40 focus-visible:border-terracotta"
          />
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => onSubmit(rating, reasons, comment.trim())}
            className="mt-2 rounded-full bg-terracotta px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40"
          >
            Submit
          </button>
        </>
      )}
    </div>
  );
}
