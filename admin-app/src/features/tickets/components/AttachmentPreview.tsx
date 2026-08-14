import { useState } from "react";

const VIDEO_EXTENSIONS = [".mp4", ".mov", ".webm", ".m4v"];

export function AttachmentPreview({ url }: { url: string | null }) {
  const [failed, setFailed] = useState(false);

  if (!url) return null;

  const isVideo = VIDEO_EXTENSIONS.some((ext) => url.toLowerCase().endsWith(ext));

  return (
    <div className="rounded-xl border border-night/10 bg-cream p-3">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-night/40">Attachment</p>
      {failed ? (
        <p className="text-sm text-night/50">Preview unavailable — {url}</p>
      ) : isVideo ? (
        <video
          src={url}
          controls
          className="max-h-56 w-full rounded-lg object-cover"
          onError={() => setFailed(true)}
        />
      ) : (
        <img
          src={url}
          alt="Ticket attachment"
          className="max-h-56 w-full rounded-lg object-cover"
          onError={() => setFailed(true)}
        />
      )}
    </div>
  );
}
