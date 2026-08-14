import { useMutation } from "@tanstack/react-query";

import { api } from "../../../lib/apiClient";

export type SyncSheetsResult = Record<string, number | string>;

export function useSyncSheets() {
  return useMutation({
    mutationFn: () => api.post<SyncSheetsResult>("/api/admin/sync-sheets"),
  });
}
