import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppShell } from "./layout/AppShell";
import { ChatPage } from "./features/chat/pages/ChatPage";
import { TicketDetailPage } from "./features/tickets/pages/TicketDetailPage";
import { TicketsListPage } from "./features/tickets/pages/TicketsListPage";

const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AppShell>
        <ChatPage />
      </AppShell>
    ),
  },
  {
    path: "/tickets",
    element: (
      <AppShell>
        <TicketsListPage />
      </AppShell>
    ),
  },
  {
    path: "/tickets/:id",
    element: (
      <AppShell>
        <TicketDetailPage />
      </AppShell>
    ),
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
