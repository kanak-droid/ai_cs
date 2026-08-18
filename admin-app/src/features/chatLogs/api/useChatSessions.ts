import { useQuery } from "@tanstack/react-query";

import { fetchChatSessions } from "./chatLogsApi";

export function useChatSessions() {
  return useQuery({
    queryKey: ["admin", "chat-sessions"],
    queryFn: fetchChatSessions,
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  });
}
