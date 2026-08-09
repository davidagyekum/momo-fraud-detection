import {
  useEffect,
  useMemo,
  useSyncExternalStore,
  type PropsWithChildren,
} from "react";
import { AuthContext, type AuthContextValue } from "./context";
import { PortalSession } from "./session";

const session = new PortalSession();

export function AuthProvider({ children }: PropsWithChildren): React.ReactNode {
  const snapshot = useSyncExternalStore(
    session.subscribe,
    session.getSnapshot,
    session.getSnapshot,
  );

  useEffect(() => {
    void session.restore();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...snapshot,
      signIn: (email, password) => session.signIn(email, password),
      signOut: () => session.signOut(),
      request: <T,>(path: string, init?: RequestInit) =>
        session.request<T>(path, init),
      accessTokenForDownload: () => session.accessTokenForDownload(),
      download: (path, suggestedName) => session.download(path, suggestedName),
    }),
    [snapshot],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
