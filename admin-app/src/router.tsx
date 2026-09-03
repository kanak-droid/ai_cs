import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import { RequireAuth } from "./auth/RequireAuth";
import { AdminsPage } from "./features/admins/pages/AdminsPage";
import { AnalyticsPage } from "./features/analytics/pages/AnalyticsPage";
import { LoginPage } from "./features/auth/pages/LoginPage";
import { CallLogDetailPage } from "./features/callLogs/pages/CallLogDetailPage";
import { CallLogsPage } from "./features/callLogs/pages/CallLogsPage";
import { ChatLogsPage } from "./features/chatLogs/pages/ChatLogsPage";
import { ChatSessionDetailPage } from "./features/chatLogs/pages/ChatSessionDetailPage";
import { EmailLogPage } from "./features/emailLog/pages/EmailLogPage";
import { SheetsSyncPage } from "./features/sheetsSync/pages/SheetsSyncPage";
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
    path: "/call-logs",
    element: (
      <RequireAuth>
        <AppShell>
          <CallLogsPage />
        </AppShell>
      </RequireAuth>
    ),
  },
  {
    path: "/call-logs/:id",
    element: (
      <RequireAuth>
        <AppShell>
          <CallLogDetailPage />
        </AppShell>
      </RequireAuth>
    ),
  },
  {
    path: "/chat-logs",
    element: (
      <RequireAuth>
        <AppShell>
          <ChatLogsPage />
        </AppShell>
      </RequireAuth>
    ),
  },
  {
    path: "/chat-logs/:id",
    element: (
      <RequireAuth>
        <AppShell>
          <ChatSessionDetailPage />
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
  {
    path: "/analytics",
    element: (
      <RequireAuth>
        <AppShell>
          <AnalyticsPage />
        </AppShell>
      </RequireAuth>
    ),
  },
  {
    path: "/email-log",
    element: (
      <RequireAuth>
        <AppShell>
          <EmailLogPage />
        </AppShell>
      </RequireAuth>
    ),
  },
  {
    path: "/sheets-sync",
    element: (
      <RequireAuth>
        <AppShell>
          <SheetsSyncPage />
        </AppShell>
      </RequireAuth>
    ),
  },
  {
    path: "/admins",
    element: (
      <RequireAuth>
        <AppShell>
          <AdminsPage />
        </AppShell>
      </RequireAuth>
    ),
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
