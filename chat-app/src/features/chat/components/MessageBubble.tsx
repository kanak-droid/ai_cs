import type { DisplayMessage } from "../types";
import { FeedbackWidget } from "./FeedbackWidget";
import { ToolActionIndicator } from "./ToolActionIndicator";

// The model sometimes emphasizes a date/amount with **markdown bold** — render
// that instead of showing the literal asterisks, without pulling in a full
// markdown library for one tag.
function renderFormattedText(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export function MessageBubble({
  message,
  onFeedbackSubmit,
  onTicketSatisfaction,
}: {
  message: DisplayMessage;
  onFeedbackSubmit: (rating: number, comment: string) => void;
  onTicketSatisfaction: (ticketId: number, satisfied: boolean) => void;
}) {
  const isAstrologer = message.role === "astrologer";

  return (
    <div className={`flex flex-col ${isAstrologer ? "items-end" : "items-start"}`}>
      {!isAstrologer && message.trace && message.trace.length > 0 && (
        <ToolActionIndicator trace={message.trace} />
      )}
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-base leading-relaxed shadow-sm ${
          isAstrologer ? "bg-terracotta text-white" : "bg-white text-ink"
        } ${message.status === "error" ? "border border-clay" : ""}`}
      >
        {message.imagePreviewUrl && message.attachmentKind === "video" ? (
          <video
            src={message.imagePreviewUrl}
            controls
            className="mb-2 max-h-48 w-full rounded-lg object-cover"
          />
        ) : (
          message.imagePreviewUrl && (
            <img
              src={message.imagePreviewUrl}
              alt="Uploaded"
              className="mb-2 max-h-48 w-full rounded-lg object-cover"
            />
          )
        )}
        <p className="whitespace-pre-wrap">{renderFormattedText(message.text)}</p>
      </div>
      {message.status === "error" && (
        <p className="mt-1 text-xs text-clay">Couldn't send — check your connection and try again.</p>
      )}
      {message.showFeedback && !message.feedbackSubmitted && (
        <FeedbackWidget onSubmit={onFeedbackSubmit} />
      )}
      {message.feedbackSubmitted && (
        <p className="mt-1 text-xs text-night/40">Thanks for the feedback!</p>
      )}
      {message.ticketSatisfactionPrompt !== undefined && (
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={() => onTicketSatisfaction(message.ticketSatisfactionPrompt!, true)}
            className="rounded-full bg-moss px-3 py-1.5 text-xs font-medium text-white"
          >
            Satisfied
          </button>
          <button
            type="button"
            onClick={() => onTicketSatisfaction(message.ticketSatisfactionPrompt!, false)}
            className="rounded-full border border-night/15 px-3 py-1.5 text-xs font-medium text-night/70"
          >
            Not satisfied
          </button>
        </div>
      )}
    </div>
  );
}
