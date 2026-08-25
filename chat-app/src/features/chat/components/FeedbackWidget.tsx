import { useState } from "react";

export function FeedbackWidget({ onSubmit }: { onSubmit: (rating: number, comment: string) => void }) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [hovered, setHovered] = useState(0);

  // Below 4 stars means something wasn't quite right — this widget has no
  // reason chips (unlike TicketRatingWidget), so a typed comment is the
  // only way to require some context on what went wrong.
  const commentRequired = rating > 0 && rating < 4;
  const canSubmit = rating > 0 && (!commentRequired || comment.trim().length > 0);

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
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder={commentRequired ? "Please tell us what went wrong" : "Anything else? (optional)"}
        rows={2}
        className="mt-2 w-full resize-none rounded-lg border border-night/15 bg-cream px-3 py-2 text-sm text-ink placeholder:text-night/40 focus-visible:border-terracotta"
      />
      <button
        type="button"
        disabled={!canSubmit}
        onClick={() => onSubmit(rating, comment.trim())}
        className="mt-2 rounded-full bg-terracotta px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40"
      >
        Submit
      </button>
    </div>
  );
}
