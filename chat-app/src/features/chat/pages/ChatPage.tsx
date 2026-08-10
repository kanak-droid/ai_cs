import { useState } from "react";
import type { ChatHistoryTurn } from "@astrohelp/shared";

import { useAstrologer } from "../../../session/AstrologerContext";
import { useSendMessage } from "../api/useSendMessage";
import { ChatComposer } from "../components/ChatComposer";
import { MessageList } from "../components/MessageList";
import type { DisplayMessage } from "../types";

let nextId = 0;
function makeId(): string {
  nextId += 1;
  return `msg-${nextId}`;
}

// "welcome" is a client-only greeting the backend never saw — everything
// else is a real turn the model needs to remember across requests (the
// backend is stateless per-call).
function toHistory(messages: DisplayMessage[]): ChatHistoryTurn[] {
  return messages
    .filter((m) => m.id !== "welcome")
    .map((m) => ({ role: m.role, text: m.text }));
}

export function ChatPage() {
  const { astrologer } = useAstrologer();
  const sendMessage = useSendMessage();
  const [messages, setMessages] = useState<DisplayMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      text: astrologer
        ? `Hi ${astrologer.name.split(" ")[0]}, how can I help you today?`
        : "Hi, how can I help you today?",
      status: "sent",
    },
  ]);

  async function handleSend(text: string, attachment?: { file: File; previewUrl: string }) {
    const history = toHistory(messages);
    const outgoingId = makeId();
    const displayText = text || "Here's my photo.";
    setMessages((prev) => [
      ...prev,
      {
        id: outgoingId,
        role: "astrologer",
        text: displayText,
        imagePreviewUrl: attachment?.previewUrl,
        status: "sending",
      },
    ]);

    const messageForBackend = attachment
      ? `${displayText}\n\n[Uploaded photo URL: ${attachment.previewUrl}]`
      : displayText;

    try {
      const response = await sendMessage.mutateAsync({ message: messageForBackend, history });
      setMessages((prev) => [
        ...prev.map((m) => (m.id === outgoingId ? { ...m, status: "sent" as const } : m)),
        {
          id: makeId(),
          role: "assistant",
          text: response.reply,
          trace: response.trace,
          status: "sent",
        },
      ]);
    } catch {
      setMessages((prev) =>
        prev.map((m) => (m.id === outgoingId ? { ...m, status: "error" as const } : m)),
      );
    }
  }

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-night/10 bg-white px-4 py-3">
        <h1 className="font-display text-xl font-semibold text-night">AstroHelp</h1>
        <p className="text-xs text-night/50">Usually replies instantly</p>
      </header>
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} isWaitingForReply={sendMessage.isPending} />
      </div>
      <ChatComposer onSend={handleSend} disabled={sendMessage.isPending} />
    </div>
  );
}
