import { useQuery } from "@tanstack/react-query";

import { fetchCallLogDetail } from "./callLogsApi";

export function useCallLogDetail(id: number) {
  return useQuery({
    queryKey: ["admin", "call-logs", id],
    queryFn: () => fetchCallLogDetail(id),
  });
}
