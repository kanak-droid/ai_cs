import type { ReactNode } from "react";

import { TabBar } from "./TabBar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen flex-col bg-cream">
      <main className="flex-1 overflow-y-auto">{children}</main>
      <TabBar />
    </div>
  );
}
