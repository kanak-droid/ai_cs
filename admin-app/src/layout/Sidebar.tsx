import { NavLink } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/Button";

const NAV_ITEMS = [
  { to: "/tickets", label: "Tickets" },
  { to: "/chat-logs", label: "Chatbot" },
  { to: "/call-logs", label: "AI Calls" },
  { to: "/analytics", label: "Analytics" },
  { to: "/admins", label: "Admins", requiresAdminAccess: true },
  { to: "/slack-log", label: "Slack Log" },
  { to: "/email-log", label: "Email Log" },
  { to: "/sheets-sync", label: "Sheets Sync" },
];

export function Sidebar() {
  const { admin, logout } = useAuth();
  const navItems = NAV_ITEMS.filter((item) => !item.requiresAdminAccess || admin?.accessLevel === "admin");

  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col border-r border-night/10 bg-night text-white">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <img src="/astrolokal-logo.png" alt="" className="h-8 w-8 shrink-0" />
        <div>
          <p className="font-display text-lg font-semibold">AstroLokal</p>
          <p className="text-xs text-white/50">Support Admin</p>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 px-3" aria-label="Primary">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 px-3 py-4">
        <p className="truncate px-3 pb-2 text-xs text-white/50">{admin?.email}</p>
        <Button variant="secondary" className="w-full" onClick={logout}>
          Log out
        </Button>
      </div>
    </aside>
  );
}
