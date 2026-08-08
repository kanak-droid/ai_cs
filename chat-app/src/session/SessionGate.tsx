import type { ReactNode } from "react";

import { EmptyState } from "../components/EmptyState";
import { Spinner } from "../components/Spinner";
import { useAstrologer } from "./AstrologerContext";

export function SessionGate({ children }: { children: ReactNode }) {
  const { status } = useAstrologer();

  if (status === "pending") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream">
        <Spinner label="Connecting you to AstroHelp…" />
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream px-6">
        <EmptyState
          title="This session has expired"
          description="Please close this window and reopen chat support from the AstroLokal app."
        />
      </div>
    );
  }

  return <>{children}</>;
}
