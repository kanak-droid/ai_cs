import { useEffect, useRef, useState } from "react";
import { STATUS_LABELS, type ChatHistoryTurn } from "@astrohelp/shared";
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
import { IDLE_RESET_MS, isIdleExpired, loadPersistedChat, savePersistedChat } from "../persistedChat";
import type { DisplayMessage } from "../types";

// Checked periodically (see the interval effect below) so a chat left open
// and idle in the background still resets without needing a reload —
// frequent enough to catch the 4-hour mark promptly, cheap enough not to matter.
const IDLE_CHECK_INTERVAL_MS = 60 * 1000;

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

// "no_visibility" -> "no visibility" — same convention admin-app uses when
// displaying a ticket's category, so the astrologer sees the same plain
// phrasing an admin would.
function categoryLabel(category: string): string {
  return category.replace(/_/g, " ");
}

function welcomeMessage(astrologer: { name: string } | null): DisplayMessage {
  const greeting = astrologer
    ? `Hi ${casualFirstName(astrologer.name)}, how can I help you today?`
    : "Hi, how can I help you today?";
  return {
    id: "welcome",
    role: "assistant",
    text: `${greeting} (If this chat sits idle for 4 hours, it'll automatically reset and start fresh.)`,
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
  const rawPersisted = astrologer ? loadPersistedChat(astrologer.astrologerId) : null;
  // Idle too long — treat it as if nothing was persisted rather than
  // resurrecting a stale conversation the astrologer has long since walked
  // away from (see "Do One more thing" ask: reset after 4h of inactivity).
  const persisted = rawPersisted && !isIdleExpired(rawPersisted) ? rawPersisted : null;

  // Persists across re-renders so a resolved ticket is announced exactly
  // once per webview visit, however many times the 15s ticket poll ticks
  // over while it's still sitting there unanswered.
  const announcedResolvedTicketIds = useRef<Set<number>>(
    new Set(persisted?.announcedResolvedTicketIds ?? []),
  );
  // NOT persisted — deliberately reseeds fresh on every mount, so a
  // ticket's pre-existing status (from before this chat page was ever
  // opened, or from an earlier visit) never fires a "new" announcement;
  // only a genuine transition observed while this page is open does. The
  // resolved-with-no-response prompt above is the one exception that IS
  // persisted/re-announced across visits — it's meant to keep nagging
  // until answered, unlike a plain status FYI.
  const lastAnnouncedStatus = useRef<Record<number, string>>({});
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
  // A ref (not state) — read inside the idle-check interval and handleSend
  // without needing either to be in a dependency array, and updated
  // synchronously (unlike setState) so the very next save-effect run
  // persists the up-to-date value.
  const lastActivityAt = useRef<number>(persisted?.lastActivityAt ?? Date.now());

  useEffect(() => {
    if (!astrologer) return;
    savePersistedChat(astrologer.astrologerId, {
      sessionId,
      messages,
      announcedResolvedTicketIds: Array.from(announcedResolvedTicketIds.current),
      chatClosed,
      lastActivityAt: lastActivityAt.current,
    });
  }, [astrologer, sessionId, messages, chatClosed]);

  function handleStartNewChat() {
    announcedResolvedTicketIds.current.clear();
    setSessionId(crypto.randomUUID());
    setMessages([welcomeMessage(astrologer)]);
    setChatClosed(false);
    lastActivityAt.current = Date.now();
  }

  // Covers the astrologer leaving the webview open in the background past
  // the 4-hour mark without ever reloading it — without this, an idle chat
  // would only reset the NEXT time the page happens to remount.
  useEffect(() => {
    const hasContentToReset = messages.length > 1 || chatClosed;
    if (!hasContentToReset) return;
    const interval = setInterval(() => {
      if (Date.now() - lastActivityAt.current > IDLE_RESET_MS) {
        handleStartNewChat();
      }
    }, IDLE_CHECK_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [messages.length, chatClosed]);

  // Proactively surface every ticket status change (admin side) in the
  // chat itself, instead of leaving the astrologer to notice a passive
  // banner. "Resolved" is the one status that gets the interactive
  // satisfied/not-satisfied prompt (see ticketSatisfactionPrompt) — it's
  // the only status where "are you satisfied with this?" is a meaningful
  // question. Every other transition (including the 48h auto-close) gets
  // a plain FYI message with whatever comment the KAM/CS left.
  useEffect(() => {
    if (!tickets) return;
    for (const ticket of tickets) {
      const latestNote = ticket.history[ticket.history.length - 1]?.note;

      if (
        ticket.status === "resolved" &&
        !ticket.satisfaction &&
        !announcedResolvedTicketIds.current.has(ticket.id)
      ) {
        announcedResolvedTicketIds.current.add(ticket.id);
        lastAnnouncedStatus.current[ticket.id] = ticket.status;
        setMessages((prev) => [
          ...prev,
          {
            id: makeId(),
            role: "assistant",
            text: `Good news — regarding your ${categoryLabel(ticket.category)} issue, your ticket #${ticket.id} is marked **Resolved** by our team.${latestNote ? ` **${latestNote}**` : ""} Did this fix your issue?`,
            status: "sent",
            ticketSatisfactionPrompt: ticket.id,
          },
        ]);
        continue;
      }

      const previousStatus = lastAnnouncedStatus.current[ticket.id];
      lastAnnouncedStatus.current[ticket.id] = ticket.status;
      // Not resolved (anymore) — a stale Satisfied/Not-satisfied prompt
      // from before (e.g. the ticket auto-closed while unanswered) would
      // 400 if clicked now (record_satisfaction requires status===resolved
      // server-side), so clear it rather than leave a dead button.
      if (ticket.status !== "resolved") {
        setMessages((prev) =>
          prev.map((m) =>
            m.ticketSatisfactionPrompt === ticket.id ? { ...m, ticketSatisfactionPrompt: undefined } : m,
          ),
        );
      }
      if (previousStatus === undefined || previousStatus === ticket.status) continue;
      // Closed via the astrologer's own "Satisfied" click seconds ago —
      // they already told us themselves; a generic FYI right after that
      // is pure noise, not new information (confirmed live: this read as
      // a confusing near-duplicate of their own action).
      if (ticket.status === "closed" && ticket.satisfaction === "satisfied") continue;

      const intro = `Regarding your ${categoryLabel(ticket.category)} issue, your ticket #${ticket.id}`;
      const text =
        ticket.status === "closed" && ticket.satisfaction === null
          ? `${intro} was automatically marked **Closed** after 48 hours with no response. Still an issue? Just tell me and I'll reopen it.`
          : `${intro} is marked **${STATUS_LABELS[ticket.status]}** by our team.${latestNote ? ` **${latestNote}**` : ""}`;
      setMessages((prev) => [
        ...prev,
        { id: makeId(), role: "assistant", text, status: "sent", isTicketStatusUpdate: true },
      ]);
    }
  }, [tickets]);

  function handleTicketSatisfaction(messageId: string, ticketId: number, satisfied: boolean) {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, ticketSatisfactionPrompt: undefined } : m)),
    );
    submitSatisfaction.mutate(
      { id: ticketId, satisfied },
      {
        onSuccess: () => {
          if (satisfied) return;
          // Pre-seed so the ticket-watcher effect's next poll doesn't
          // re-announce this exact transition as a generic FYI —
          // handleUnsatisfied already says it, right here, immediately.
          lastAnnouncedStatus.current[ticketId] = "under_review";
          handleUnsatisfied();
        },
      },
    );
  }

  async function handleSend(
    text: string,
    attachment?: { file: File; previewUrl: string },
    options?: { resolveMarker?: boolean },
  ) {
    const history = toHistory(messages);
    lastActivityAt.current = Date.now();
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
      // A fixed, unambiguous marker (same convention as the attachment-URL
      // one above) — the "did this fix it?" button's click sends this
      // instead of asking the astrologer to type a confirmation themselves.
      // See prompt.py: this exact marker always counts as a confirmed
      // resolution, even after a simple factual lookup that wouldn't
      // otherwise have prompted for one.
      if (options?.resolveMarker) {
        backendText = `${backendText}\n\n[Astrologer confirmed: Yes, this solved my issue. Please close this chat now.]`;
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

  function handleResolveConfirm() {
    handleSend("Yes, that solved it — please close this chat.", undefined, { resolveMarker: true });
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
          chatClosed={chatClosed}
          onFeedbackSubmit={handleFeedbackSubmit}
          onTicketSatisfaction={handleTicketSatisfaction}
          onResolveConfirm={handleResolveConfirm}
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
        <div className="bg-white">
          {messages.length === 1 && (
            <FaqChips onPick={(question) => handleSend(question)} disabled={sendMessage.isPending} />
          )}
          <ChatComposer onSend={handleSend} disabled={sendMessage.isPending} />
          <div className="flex justify-center border-t border-night/5 py-1.5">
            <button
              type="button"
              onClick={handleStartNewChat}
              className="text-xs font-medium text-night/40 underline decoration-night/20 hover:text-night/60"
            >
              Start a new chat
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
