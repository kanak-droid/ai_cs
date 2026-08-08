import { useState } from "react";

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
      const response = await sendMessage.mutateAsync(messageForBackend);
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
        <h1 className="text-lg font-medium text-night">AstroHelp</h1>
        <p className="text-xs text-night/50">Usually replies instantly</p>
      </header>
      <div className="flex-1 overflow-y-auto">
        <MessageList messages={messages} isWaitingForReply={sendMessage.isPending} />
      </div>
      <ChatComposer onSend={handleSend} disabled={sendMessage.isPending} />
    </div>
  );
}
