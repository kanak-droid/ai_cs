import type { DisplayMessage } from "./types";

// sessionStorage (not localStorage) deliberately — survives a reload or
// switching to "My Tickets" and back (ChatPage fully unmounts on route
// change, which would otherwise wipe its local useState), but still clears
// itself the moment the webview tab actually closes, unlike localStorage.
export interface PersistedChatState {
  sessionId: string;
  messages: DisplayMessage[];
  announcedResolvedTicketIds: number[];
  // A ticket raised or an issue resolved ends this thread — the astrologer
  // sees a feedback prompt and a "start a new chat" option instead of being
  // able to keep typing into the same thread (see ChatPage.tsx).
  chatClosed: boolean;
}

function storageKey(astrologerId: number): string {
  return `astrohelp:chat:${astrologerId}`;
}

export function loadPersistedChat(astrologerId: number): PersistedChatState | null {
  try {
    const raw = sessionStorage.getItem(storageKey(astrologerId));
    return raw ? (JSON.parse(raw) as PersistedChatState) : null;
  } catch {
    return null;
  }
}

export function savePersistedChat(astrologerId: number, state: PersistedChatState): void {
  try {
    sessionStorage.setItem(storageKey(astrologerId), JSON.stringify(state));
  } catch {
    // Private-browsing modes can throw here — losing persistence is fine,
    // the chat still works for the rest of this tab's life either way.
  }
}
