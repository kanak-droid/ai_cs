import type { DisplayMessage } from "../types";
import { ToolActionIndicator } from "./ToolActionIndicator";

export function MessageBubble({ message }: { message: DisplayMessage }) {
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
        {message.imagePreviewUrl && (
          <img
            src={message.imagePreviewUrl}
            alt="Uploaded"
            className="mb-2 max-h-48 w-full rounded-lg object-cover"
          />
        )}
        <p className="whitespace-pre-wrap">{message.text}</p>
      </div>
      {message.status === "error" && (
        <p className="mt-1 text-xs text-clay">Couldn't send — check your connection and try again.</p>
      )}
    </div>
  );
}
