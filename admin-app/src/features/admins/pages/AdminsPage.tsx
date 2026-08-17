import type { Admin, AdminAccessLevel, AdminRole } from "@astrohelp/shared";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthContext";
import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { ApiError } from "../../../lib/http-error";
import { useAllAdmins, useCreateAdmin, useUpdateAdmin } from "../api/useAdmins";

function parseLanguages(input: string): string[] {
  return input
    .split(",")
    .map((lang) => lang.trim())
    .filter(Boolean);
}

function AddAccessForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<AdminRole>("kam");
  const [accessLevel, setAccessLevel] = useState<AdminAccessLevel>("normal");
  const [languages, setLanguages] = useState("");
  const [slackUserId, setSlackUserId] = useState("");
  const createAdmin = useCreateAdmin();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    await createAdmin.mutateAsync({
      name,
      email,
      role,
      access_level: accessLevel,
      languages: parseLanguages(languages),
      slack_user_id: slackUserId.trim() || undefined,
    });
    setName("");
    setEmail("");
    setRole("kam");
    setAccessLevel("normal");
    setLanguages("");
    setSlackUserId("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-wrap items-end gap-3 rounded-xl border border-night/10 bg-white p-4"
    >
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-night/60">Name</span>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
        />
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-night/60">Work email</span>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
        />
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-night/60">Role</span>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as AdminRole)}
          className="rounded-lg border border-night/15 px-2 py-2 text-sm text-ink"
        >
          <option value="kam">KAM</option>
          <option value="cs">CS</option>
          <option value="others">Others</option>
        </select>
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-night/60">Access</span>
        <select
          value={accessLevel}
          onChange={(e) => setAccessLevel(e.target.value as AdminAccessLevel)}
          className="rounded-lg border border-night/15 px-2 py-2 text-sm text-ink"
        >
          <option value="normal">Normal</option>
          <option value="admin">Admin</option>
        </select>
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-night/60">Languages (CS routing)</span>
        <input
          placeholder="Hindi, Telugu"
          value={languages}
          onChange={(e) => setLanguages(e.target.value)}
          className="rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
        />
      </label>
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-night/60">Slack user ID</span>
        <input
          placeholder="U0123ABC456"
          value={slackUserId}
          onChange={(e) => setSlackUserId(e.target.value)}
          className="w-32 rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-terracotta"
        />
      </label>
      <button
        type="submit"
        disabled={createAdmin.isPending}
        className="rounded-lg bg-night px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {createAdmin.isPending ? "Adding…" : "Add access"}
      </button>
      {createAdmin.isError && (
        <p className="w-full text-sm text-clay">
          {createAdmin.error instanceof ApiError ? createAdmin.error.message : "Something went wrong."}
        </p>
      )}
    </form>
  );
}

function AdminsTable({
  admins,
  updateAdmin,
}: {
  admins: Admin[];
  updateAdmin: ReturnType<typeof useUpdateAdmin>;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-night/10 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-night/10 text-left text-xs uppercase tracking-wide text-night/40">
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">Email</th>
            <th className="px-4 py-3">Role</th>
            <th className="px-4 py-3">Access</th>
            <th className="px-4 py-3">Languages</th>
            <th className="px-4 py-3">Slack user ID</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {admins.map((admin) => (
            <tr key={admin.id} className="border-b border-night/5 last:border-0">
              <td className="px-4 py-3 font-medium text-night">{admin.name}</td>
              <td className="px-4 py-3 text-night/70">{admin.email}</td>
              <td className="px-4 py-3">
                <select
                  value={admin.role}
                  disabled={updateAdmin.isPending}
                  onChange={(e) => updateAdmin.mutate({ id: admin.id, role: e.target.value as AdminRole })}
                  className="rounded-lg border border-night/15 px-2 py-1 text-sm text-ink"
                >
                  <option value="kam">KAM</option>
                  <option value="cs">CS</option>
                  <option value="others">Others</option>
                </select>
              </td>
              <td className="px-4 py-3">
                <select
                  value={admin.access_level}
                  disabled={updateAdmin.isPending}
                  onChange={(e) =>
                    updateAdmin.mutate({
                      id: admin.id,
                      access_level: e.target.value as AdminAccessLevel,
                    })
                  }
                  className="rounded-lg border border-night/15 px-2 py-1 text-sm text-ink"
                >
                  <option value="normal">Normal</option>
                  <option value="admin">Admin</option>
                </select>
              </td>
              <td className="px-4 py-3">
                <input
                  key={admin.languages.join(",")}
                  defaultValue={admin.languages.join(", ")}
                  placeholder="Hindi, Telugu"
                  disabled={updateAdmin.isPending}
                  onBlur={(e) =>
                    updateAdmin.mutate({ id: admin.id, languages: parseLanguages(e.target.value) })
                  }
                  className="w-36 rounded-lg border border-night/15 px-2 py-1 text-sm text-ink"
                />
              </td>
              <td className="px-4 py-3">
                <input
                  key={admin.slack_user_id ?? ""}
                  defaultValue={admin.slack_user_id ?? ""}
                  placeholder="U0123ABC456"
                  disabled={updateAdmin.isPending}
                  onBlur={(e) => {
                    const value = e.target.value.trim();
                    if (value) updateAdmin.mutate({ id: admin.id, slack_user_id: value });
                  }}
                  className="w-32 rounded-lg border border-night/15 px-2 py-1 text-sm text-ink"
                />
              </td>
              <td className="px-4 py-3">
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                    admin.is_active ? "bg-moss/15 text-moss" : "bg-night/10 text-night/50"
                  }`}
                >
                  {admin.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  type="button"
                  disabled={updateAdmin.isPending}
                  onClick={() => updateAdmin.mutate({ id: admin.id, is_active: !admin.is_active })}
                  className="text-sm font-medium text-terracotta hover:underline disabled:opacity-50"
                >
                  {admin.is_active ? "Deactivate" : "Reactivate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AdminsPage() {
  const { admin: me } = useAuth();
  const { data: admins, status } = useAllAdmins();
  const updateAdmin = useUpdateAdmin();

  if (me?.accessLevel !== "admin") {
    return (
      <EmptyState
        title="Admin access required"
        description="Only admins can manage who has dashboard access. Ask an existing admin to grant you admin access if you need this."
      />
    );
  }

  if (status === "pending") return <Spinner label="Loading admins…" />;
  if (status === "error" || !admins) return <EmptyState title="Couldn't load admins" />;

  const activeAdmins = admins.filter((a) => a.is_active);
  const inactiveAdmins = admins.filter((a) => !a.is_active);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="font-display text-2xl font-semibold text-night">Admins</h1>
        <p className="text-sm text-night/50">
          KAMs get tickets round-robin assigned to them personally. CS admins get tickets round-robin
          assigned within whichever of their languages matches the astrologer's — set a CS admin's
          languages below to put them in that rotation. Access level controls who can manage this
          page — Normal-access accounts log in with{" "}
          <span className="font-medium text-night/70">astroHelp@123</span>, admin-access accounts with{" "}
          <span className="font-medium text-night/70">astroHelpAdmin@123</span>. Deactivate a profile
          here instead of deleting it to keep its ticket history intact. Set a Slack user ID (from
          that person's Slack profile → "..." → Copy member ID) to have ticket notifications actually
          @mention and notify them — without it, their name still shows in the message, but Slack
          never pings them.
        </p>
      </div>

      <AddAccessForm />

      <AdminsTable admins={activeAdmins} updateAdmin={updateAdmin} />

      <div className="mt-2 flex flex-col gap-2">
        <h2 className="text-sm font-medium uppercase tracking-wide text-night/40">
          Deactivated ({inactiveAdmins.length})
        </h2>
        {inactiveAdmins.length === 0 ? (
          <p className="text-sm text-night/40">No deactivated accounts.</p>
        ) : (
          <AdminsTable admins={inactiveAdmins} updateAdmin={updateAdmin} />
        )}
      </div>
    </div>
  );
}
