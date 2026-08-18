import { useState } from "react";

import { useTicketAttachmentPreview } from "../api/useTicketAttachmentPreview";

const VIDEO_EXTENSIONS = [".mp4", ".mov", ".webm", ".m4v"];

export function AttachmentPreview({ ticketId, url }: { ticketId: number; url: string | null }) {
  const [failed, setFailed] = useState(false);
  const { data, status } = useTicketAttachmentPreview(ticketId, !!url);

  if (!url) return null;

  // Extension-sniffed from the raw URL, not the signed one — a presigned
  // URL's query string (the signature itself) would otherwise break a
  // simple .endsWith(ext) check.
  const isVideo = VIDEO_EXTENSIONS.some((ext) => url.toLowerCase().endsWith(ext));
  const filename = url.split("/").pop() || "attachment";
  const previewUrl = data?.preview_url;

  return (
    <div className="rounded-xl border border-night/10 bg-cream p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-night/40">Attachment</p>
        {previewUrl && !failed && (
          <a
            href={previewUrl}
            download={filename}
            className="text-xs font-medium text-terracotta hover:underline"
          >
            Download
          </a>
        )}
      </div>
      {status === "pending" ? (
        <p className="text-sm text-night/50">Loading preview…</p>
      ) : failed || status === "error" || !previewUrl ? (
        <p className="text-sm text-night/50">Preview unavailable — {url}</p>
      ) : isVideo ? (
        <video
          src={previewUrl}
          controls
          className="max-h-56 w-full rounded-lg object-cover"
          onError={() => setFailed(true)}
        />
      ) : (
        <img
          src={previewUrl}
          alt="Ticket attachment"
          className="max-h-56 w-full rounded-lg object-cover"
          onError={() => setFailed(true)}
        />
      )}
    </div>
  );
}
