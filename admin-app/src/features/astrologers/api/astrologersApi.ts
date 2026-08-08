import type { Astrologer } from "@astrohelp/shared";

import { api } from "../../../lib/apiClient";

export function fetchAstrologers(): Promise<Astrologer[]> {
  return api.get<Astrologer[]>("/api/admin/astrologers");
}
