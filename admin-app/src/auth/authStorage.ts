// Ordinary desktop browser tab, not a WebView — persisting the admin session
// across a page refresh is expected UX here, unlike the astrologer-side chat
// app's in-memory-only rule (which was specific to unreliable WebView storage).
const STORAGE_KEY = "astrohelp_admin_token";

export const authStorage = {
  getToken(): string | null {
    return localStorage.getItem(STORAGE_KEY);
  },
  setToken(token: string): void {
    localStorage.setItem(STORAGE_KEY, token);
  },
  clear(): void {
    localStorage.removeItem(STORAGE_KEY);
  },
};
