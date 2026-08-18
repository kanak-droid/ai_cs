import { useQuery } from "@tanstack/react-query";

import { api } from "../../../lib/apiClient";

interface AttachmentPreviewResponse {
  preview_url: string;
}

// A ticket's raw attachment_url (its real S3 location) 403s on a plain
// <img src> — the browser has no AWS credentials, and S3 buckets here have
// no public-read policy. This fetches a short-lived signed URL instead,
// which the browser CAN load directly, no auth header needed once issued.
export function useTicketAttachmentPreview(ticketId: number, enabled: boolean) {
  return useQuery({
    queryKey: ["admin", "tickets", ticketId, "attachment"],
    queryFn: () => api.get<AttachmentPreviewResponse>(`/api/admin/tickets/${ticketId}/attachment`),
    enabled,
    // The signed URL is valid for 1hr server-side — refetching well before
    // that keeps a long-open ticket detail page from showing an expired link.
    staleTime: 45 * 60_000,
  });
}
