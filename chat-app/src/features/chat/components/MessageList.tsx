import { useEffect, useRef } from "react";

import type { DisplayMessage } from "../types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

export function MessageList({
  messages,
  isWaitingForReply,
  onFeedbackSubmit,
  onTicketSatisfaction,
}: {
  messages: DisplayMessage[];
  isWaitingForReply: boolean;
  onFeedbackSubmit: (messageId: string, rating: number, comment: string) => void;
  onTicketSatisfaction: (messageId: string, ticketId: number, satisfied: boolean) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, isWaitingForReply]);

  return (
    <div className="flex flex-col gap-3 px-4 py-4">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          onFeedbackSubmit={(rating, comment) => onFeedbackSubmit(message.id, rating, comment)}
          onTicketSatisfaction={(ticketId, satisfied) =>
            onTicketSatisfaction(message.id, ticketId, satisfied)
          }
        />
      ))}
      {isWaitingForReply && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
