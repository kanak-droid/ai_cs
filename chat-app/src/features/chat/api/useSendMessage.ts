import { useMutation } from "@tanstack/react-query";
import type { ChatHistoryTurn } from "@astrohelp/shared";

import { sendChatMessage } from "./chatApi";

export function useSendMessage() {
  return useMutation({
    mutationFn: (vars: { message: string; history: ChatHistoryTurn[] }) =>
      sendChatMessage(vars.message, vars.history),
  });
}
