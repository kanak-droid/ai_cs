import { useState } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../../../auth/AuthContext";
import { authStorage } from "../../../auth/authStorage";
import { Button } from "../../../components/Button";
import { ApiError } from "../../../lib/http-error";
import { useLogin } from "../api/useLogin";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();
  const { login: setSession } = useAuth();

  if (authStorage.getToken()) {
    return <Navigate to="/tickets" replace />;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const result = await login.mutateAsync({ email, password });
    await setSession(result.access_token);
    window.location.assign("/tickets");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-cloudline px-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-semibold text-night">AstroHelp</h1>
        <p className="mt-1 text-sm text-night/50">Admin sign in</p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-night">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-harbor"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-night">Password</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-lg border border-night/15 px-3 py-2 text-sm text-ink focus-visible:border-harbor"
            />
          </label>

          {login.isError && (
            <p className="text-sm text-clay">
              {login.error instanceof ApiError ? login.error.message : "Something went wrong."}
            </p>
          )}

          <Button type="submit" disabled={login.isPending} className="mt-2 w-full">
            {login.isPending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}
