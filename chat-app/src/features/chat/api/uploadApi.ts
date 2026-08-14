// Multipart upload bypasses the shared `api` client (which always JSON-encodes
// the body) — this posts FormData directly, with only the auth header attached.
import { getAuthToken } from "../../../lib/apiClient";

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function uploadAttachment(file: File): Promise<{ url: string }> {
  const token = getAuthToken();
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${BASE_URL}/api/uploads`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body,
  });

  if (!response.ok) {
    throw new Error("Upload failed");
  }
  return response.json();
}
