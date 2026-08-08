import { QueryProvider } from "./app/QueryProvider";
import { AppRouter } from "./router";
import { AstrologerProvider } from "./session/AstrologerContext";
import { SessionGate } from "./session/SessionGate";

export function App() {
  return (
    <QueryProvider>
      <AstrologerProvider>
        <SessionGate>
          <AppRouter />
        </SessionGate>
      </AstrologerProvider>
    </QueryProvider>
  );
}
