import { useState } from "react";

import { PhotoUploadButton } from "./PhotoUploadButton";

interface PendingAttachment {
  file: File;
  previewUrl: string;
}

interface ChatComposerProps {
  disabled?: boolean;
  onSend: (text: string, attachment?: PendingAttachment) => void;
}

export function ChatComposer({ disabled, onSend }: ChatComposerProps) {
  const [text, setText] = useState("");
  const [attachment, setAttachment] = useState<PendingAttachment | null>(null);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (disabled) return;
    if (!text.trim() && !attachment) return;
    onSend(text.trim(), attachment ?? undefined);
    setText("");
    setAttachment(null);
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-night/10 bg-white p-3">
      {attachment && (
        <div className="mb-2 flex items-center gap-2 rounded-lg bg-cream px-2 py-1.5">
          {attachment.file.type.startsWith("video/") ? (
            <video src={attachment.previewUrl} className="h-10 w-10 rounded object-cover" />
          ) : (
            <img src={attachment.previewUrl} alt="" className="h-10 w-10 rounded object-cover" />
          )}
          <span className="flex-1 truncate text-xs text-night/60">{attachment.file.name}</span>
          <button
            type="button"
            onClick={() => setAttachment(null)}
            className="text-xs text-night/50 underline"
          >
            Remove
          </button>
        </div>
      )}
      <div className="flex items-end gap-1.5">
        <PhotoUploadButton
          disabled={disabled}
          onSelect={(file, previewUrl) => setAttachment({ file, previewUrl })}
        />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder="Type your message…"
          rows={1}
          disabled={disabled}
          className="max-h-32 flex-1 resize-none rounded-2xl border border-night/15 bg-cream px-4 py-2.5 text-base text-ink placeholder:text-night/40 focus-visible:border-terracotta disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={disabled || (!text.trim() && !attachment)}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-terracotta text-white transition-opacity disabled:opacity-40"
          aria-label="Send message"
        >
          <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
            <path
              d="M4 12h15m0 0-6-6m6 6-6 6"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </form>
  );
}
