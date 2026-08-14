import { useEffect, useRef, useState } from "react";
import type { ChatHistoryTurn } from "@astrohelp/shared";
import { useQueryClient } from "@tanstack/react-query";

import { useAstrologer } from "../../../session/AstrologerContext";
import { casualFirstName } from "../../../lib/casualFirstName";
import { ticketsKeys } from "../../tickets/api/queryKeys";
import { useSubmitSatisfaction } from "../../tickets/api/useSubmitSatisfaction";
import { useTickets } from "../../tickets/api/useTickets";
import { submitSessionFeedback } from "../api/feedbackApi";
import { uploadAttachment } from "../api/uploadApi";
import { useSendMessage } from "../api/useSendMessage";
import { ChatComposer } from "../components/ChatComposer";
import { FaqChips } from "../components/FaqChips";
import { MessageList } from "../components/MessageList";
import { TicketStatusBanner } from "../components/TicketStatusBanner";
import { loadPersistedChat, savePersistedChat } from "../persistedChat";
import type { DisplayMessage } from "../types";

// A restored (persisted) session can already contain ids from before a
// reload — an incrementing counter reset to 0 on module (re)load would risk
// colliding with those and confusing React's reconciliation, so use a
// collision-resistant id instead.
function makeId(): string {
  return `msg-${crypto.randomUUID()}`;
}

// "welcome" is a client-only greeting the backend never saw — everything
// else is a real turn the model needs to remember across requests (the
// backend is stateless per-call). Use backendText (which carries any
// attachment-URL marker) rather than the clean display text, so a photo/video
// shared several turns ago is still resend-able as history, not just on the
// one request it was uploaded with.
function toHistory(messages: DisplayMessage[]): ChatHistoryTurn[] {
  return messages
    .filter((m) => m.id !== "welcome")
    .map((m) => ({ role: m.role, text: m.backendText ?? m.text }));
}

function welcomeMessage(astrologer: { name: string } | null): DisplayMessage {
  return {
    id: "welcome",
    role: "assistant",
    text: astrologer
      ? `Hi ${casualFirstName(astrologer.name)}, how can I help you today?`
      : "Hi, how can I help you today?",
    status: "sent",
  };
}

export function ChatPage() {
  const { astrologer } = useAstrologer();
  const sendMessage = useSendMessage();
  const queryClient = useQueryClient();
  const { data: tickets } = useTickets();
  const submitSatisfaction = useSubmitSatisfaction();
  // Restored from sessionStorage when present — otherwise the transcript
  // (and the ticket-announcement/session-id state below) would reset every
  // time ChatPage unmounts, which react-router does on every route change
  // (e.g. visiting "My Tickets" and coming back) and on a full reload.
  // sessionStorage rather than localStorage: it clears itself once the
  // webview tab actually closes, rather than persisting indefinitely on-device.
  const persisted = astrologer ? loadPersistedChat(astrologer.astrologerId) : null;

  // Persists across re-renders so a resolved ticket is announced exactly
  // once per webview visit, however many times the 15s ticket poll ticks
  // over while it's still sitting there unanswered.
  const announcedResolvedTicketIds = useRef<Set<number>>(
    new Set(persisted?.announcedResolvedTicketIds ?? []),
  );
  // One per webview visit — analytics-only (see ChatSession on the backend),
  // never used for anything the astrologer-facing flows depend on.
  const [sessionId, setSessionId] = useState(() => persisted?.sessionId ?? crypto.randomUUID());
  const [messages, setMessages] = useState<DisplayMessage[]>(() => persisted?.messages ?? [welcomeMessage(astrologer)]);
  // A ticket raised or an issue resolved ends this thread (see show_feedback
  // handling in handleSend) — the composer locks and a "start a new chat"
  // option appears instead. Without this, the model kept seeing an
  // already-resolved topic's back-and-forth as part of the SAME history for
  // a completely unrelated new issue raised right after, and it visibly
  // affected its behavior on that new issue.
  const [chatClosed, setChatClosed] = useState(() => persisted?.chatClosed ?? false);

  useEffect(() => {
    if (!astrologer) return;
    savePersistedChat(astrologer.astrologerId, {
      sessionId,
      messages,
      announcedResolvedTicketIds: Array.from(announcedResolvedTicketIds.current),
      chatClosed,
    });
  }, [astrologer, sessionId, messages, chatClosed]);

  function handleStartNewChat() {
    announcedResolvedTicketIds.current.clear();
    setSessionId(crypto.randomUUID());
    setMessages([welcomeMessage(astrologer)]);
    setChatClosed(false);
  }

  // Proactively announce a ticket the moment it's resolved (admin side),
  // instead of leaving the astrologer to notice a passive banner — this is
  // how "did we ask satisfied/unsatisfied?" actually gets asked.
  useEffect(() => {
    if (!tickets) return;
    for (const ticket of tickets) {
      if (
        ticket.status === "resolved" &&
        !ticket.satisfaction &&
        !announcedResolvedTicketIds.current.has(ticket.id)
      ) {
        announcedResolvedTicketIds.current.add(ticket.id);
        setMessages((prev) => [
          ...prev,
          {
            id: makeId(),
            role: "assistant",
            text: `Good news — Ticket #${ticket.id} has been marked resolved by our team! Did this fix your issue?`,
            status: "sent",
            ticketSatisfactionPrompt: ticket.id,
          },
        ]);
      }
    }
  }, [tickets]);

  function handleTicketSatisfaction(messageId: string, ticketId: number, satisfied: boolean) {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, ticketSatisfactionPrompt: undefined } : m)),
    );
    submitSatisfaction.mutate(
      { id: ticketId, satisfied },
      { onSuccess: () => { if (!satisfied) handleUnsatisfied(); } },
    );
  }

  async function handleSend(text: string, attachment?: { file: File; previewUrl: string }) {
    const history = toHistory(messages);
    const outgoingId = makeId();
    const displayText = text || (attachment ? "Here's my photo/video." : "");
    const attachmentKind = attachment?.file.type.startsWith("video/") ? "video" : "image";
    setMessages((prev) => [
      ...prev,
      {
        id: outgoingId,
        role: "astrologer",
        text: displayText,
        imagePreviewUrl: attachment?.previewUrl,
        attachmentKind: attachment ? attachmentKind : undefined,
        status: "sending",
      },
    ]);

    try {
      let backendText = displayText;
      // The blob: URL used for the instant local preview above only lives as
      // long as this page load — swapped for the real uploaded URL once it's
      // known, so a persisted-and-reloaded transcript (see persistedChat.ts)
      // doesn't show a broken image.
      let uploadedUrl: string | undefined;
      if (attachment) {
        const { url } = await uploadAttachment(attachment.file);
        uploadedUrl = url;
        backendText = `${displayText}\n\n[Uploaded attachment URL: ${url}]`;
      }

      const response = await sendMessage.mutateAsync({ message: backendText, history, sessionId });
      setMessages((prev) => [
        ...prev.map((m) =>
          m.id === outgoingId
            ? {
                ...m,
                backendText,
                status: "sent" as const,
                imagePreviewUrl: uploadedUrl ?? m.imagePreviewUrl,
              }
            : m,
        ),
        {
          id: makeId(),
          role: "assistant",
          text: response.reply,
          trace: response.trace,
          status: "sent",
          showFeedback: response.show_feedback,
        },
      ]);
      if (response.created_ticket_id) {
        queryClient.invalidateQueries({ queryKey: ticketsKeys.list() });
      }
      // A ticket raised or an issue resolved is a terminal action for this
      // thread — closing it here is what stops a later, unrelated issue
      // from being reasoned about alongside an already-settled one.
      if (response.show_feedback) {
        setChatClosed(true);
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) => (m.id === outgoingId ? { ...m, status: "error" as const } : m)),
      );
    }
  }

  function handleFeedbackSubmit(messageId: string, rating: number, comment: string) {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, feedbackSubmitted: true } : m)),
    );
    submitSessionFeedback(sessionId, rating, comment || null).catch(() => {
      // Best-effort analytics — a failed submit shouldn't block or confuse the chat.
    });
  }

  function handleUnsatisfied() {
    // Reopens a thread that may have already closed (e.g. from the earlier
    // ticket-raising message) — the astrologer needs to actually describe
    // what's still wrong, which means the composer has to accept input again.
    setChatClosed(false);
    setMessages((prev) => [
      ...prev,
      {
        id: makeId(),
        role: "assistant",
        text: "I'm sorry that didn't fully resolve it. Please tell me what's still wrong and I'll take it from there.",
        status: "sent",
      },
    ]);
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center gap-2.5 border-b border-night/10 bg-white px-4 py-3">
        <img src="/astrolokal-logo.png" alt="" className="h-9 w-9 shrink-0" />
        <div>
          <h1 className="font-display text-xl font-semibold text-night">AstroLokal</h1>
          <p className="text-xs text-night/50">Usually replies instantly</p>
        </div>
      </header>
      <div className="flex-1 overflow-y-auto">
        <MessageList
          messages={messages}
          isWaitingForReply={sendMessage.isPending}
          onFeedbackSubmit={handleFeedbackSubmit}
          onTicketSatisfaction={handleTicketSatisfaction}
        />
      </div>
      <TicketStatusBanner />
      {chatClosed ? (
        <div className="border-t border-night/10 bg-white p-4 text-center">
          <p className="mb-3 text-sm text-night/60">This chat has ended.</p>
          <button
            type="button"
            onClick={handleStartNewChat}
            className="rounded-full bg-terracotta px-5 py-2 text-sm font-medium text-white"
          >
            Start a new chat
          </button>
        </div>
      ) : (
        <>
          {messages.length === 1 && (
            <FaqChips onPick={(question) => handleSend(question)} disabled={sendMessage.isPending} />
          )}
          <ChatComposer onSend={handleSend} disabled={sendMessage.isPending} />
        </>
      )}
    </div>
  );
}
