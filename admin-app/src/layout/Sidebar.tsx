import { NavLink } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Button } from "../components/Button";

const NAV_ITEMS = [
  { to: "/tickets", label: "Tickets" },
  { to: "/slack-log", label: "Slack Log" },
];

export function Sidebar() {
  const { admin, logout } = useAuth();

  return (
    <aside className="flex h-screen w-56 shrink-0 flex-col border-r border-night/10 bg-night text-white">
      <div className="px-5 py-5">
        <p className="text-base font-semibold">AstroHelp</p>
        <p className="text-xs text-white/50">Admin</p>
      </div>
      <nav className="flex flex-1 flex-col gap-0.5 px-3" aria-label="Primary">
        {NAV_ITEMS.map((item) => (
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
