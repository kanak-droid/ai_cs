import { useMutation } from "@tanstack/react-query";

import { sendChatMessage } from "./chatApi";

export function useSendMessage() {
  return useMutation({
    mutationFn: sendChatMessage,
  });
}
