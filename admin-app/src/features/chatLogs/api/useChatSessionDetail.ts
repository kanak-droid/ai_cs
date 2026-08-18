import { useQuery } from "@tanstack/react-query";

import { fetchChatSessionDetail } from "./chatLogsApi";

export function useChatSessionDetail(id: number) {
  return useQuery({
    queryKey: ["admin", "chat-sessions", id],
    queryFn: () => fetchChatSessionDetail(id),
  });
}
