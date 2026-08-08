import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import { RequireAuth } from "./auth/RequireAuth";
import { LoginPage } from "./features/auth/pages/LoginPage";
import { SlackLogPage } from "./features/slackLog/pages/SlackLogPage";
import { TicketDetailPage } from "./features/tickets/pages/TicketDetailPage";
import { TicketQueuePage } from "./features/tickets/pages/TicketQueuePage";
import { AppShell } from "./layout/AppShell";

const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/tickets" replace /> },
  { path: "/login", element: <LoginPage /> },
  {
    path: "/tickets",
    element: (
      <RequireAuth>
        <AppShell>
          <TicketQueuePage />
        </AppShell>
      </RequireAuth>
    ),
  },
  {
    path: "/tickets/:id",
    element: (
      <RequireAuth>
        <AppShell>
          <TicketDetailPage />
        </AppShell>
      </RequireAuth>
    ),
  },
  {
    path: "/slack-log",
    element: (
      <RequireAuth>
        <AppShell>
          <SlackLogPage />
        </AppShell>
      </RequireAuth>
    ),
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
