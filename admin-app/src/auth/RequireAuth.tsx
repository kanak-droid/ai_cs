import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { Spinner } from "../components/Spinner";
import { authStorage } from "./authStorage";
import { useAuth } from "./AuthContext";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { isLoading, admin } = useAuth();

  if (!authStorage.getToken()) {
    return <Navigate to="/login" replace />;
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (!admin) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
