import { useEffect, useRef } from "react";

import type { DisplayMessage } from "../types";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

export function MessageList({
  messages,
  isWaitingForReply,
}: {
  messages: DisplayMessage[];
  isWaitingForReply: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, isWaitingForReply]);

  return (
    <div className="flex flex-col gap-3 px-4 py-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isWaitingForReply && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
