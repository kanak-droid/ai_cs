import { AuthProvider } from "./auth/AuthContext";
import { QueryProvider } from "./app/QueryProvider";
import { AppRouter } from "./router";

export function App() {
  return (
    <QueryProvider>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </QueryProvider>
  );
}
