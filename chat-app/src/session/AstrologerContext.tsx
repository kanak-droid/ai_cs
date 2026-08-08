import { createContext, useContext, type ReactNode } from "react";

import type { AstrologerIdentity } from "./useAstrologerSession";
import { useAstrologerSession } from "./useAstrologerSession";

interface AstrologerSessionValue {
  astrologer: AstrologerIdentity | null;
  status: "pending" | "error" | "success";
}

const AstrologerContext = createContext<AstrologerSessionValue | undefined>(undefined);

export function AstrologerProvider({ children }: { children: ReactNode }) {
  const { data, status } = useAstrologerSession();

  return (
    <AstrologerContext.Provider value={{ astrologer: data ?? null, status }}>
      {children}
    </AstrologerContext.Provider>
  );
}

export function useAstrologer(): AstrologerSessionValue {
  const ctx = useContext(AstrologerContext);
  if (!ctx) {
    throw new Error("useAstrologer must be used within an AstrologerProvider");
  }
  return ctx;
}
