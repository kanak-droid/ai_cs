import { useQuery } from "@tanstack/react-query";

import { fetchCallLogs, type CallLogFilters } from "./callLogsApi";

export function useCallLogs(filters: CallLogFilters = {}) {
  return useQuery({
    queryKey: ["admin", "call-logs", filters],
    queryFn: () => fetchCallLogs(filters),
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });
}
