import { useEffect, useRef } from "react";

import type { DisplayMessage } from "../types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

export function MessageList({
  messages,
  isWaitingForReply,
  chatClosed,
  onFeedbackSubmit,
  onTicketSatisfaction,
  onResolveConfirm,
}: {
  messages: DisplayMessage[];
  isWaitingForReply: boolean;
  chatClosed: boolean;
  onFeedbackSubmit: (messageId: string, rating: number, comment: string) => void;
  onTicketSatisfaction: (messageId: string, ticketId: number, satisfied: boolean) => void;
  onResolveConfirm: () => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  // Derived, not stored on the message itself — the button always tracks
  // whichever assistant reply is currently the latest, with no separate
  // "clear the old one" step needed once a new message arrives.
  const lastMessageId = messages[messages.length - 1]?.id;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, isWaitingForReply]);

  return (
    <div className="flex flex-col gap-3 px-4 py-4">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          showResolvePrompt={
            !chatClosed &&
            !message.showFeedback &&
            !message.isTicketStatusUpdate &&
            message.ticketSatisfactionPrompt === undefined &&
            message.role === "assistant" &&
            message.id !== "welcome" &&
            message.id === lastMessageId
          }
          onFeedbackSubmit={(rating, comment) => onFeedbackSubmit(message.id, rating, comment)}
          onTicketSatisfaction={(ticketId, satisfied) =>
            onTicketSatisfaction(message.id, ticketId, satisfied)
          }
          onResolveConfirm={onResolveConfirm}
        />
      ))}
      {isWaitingForReply && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
