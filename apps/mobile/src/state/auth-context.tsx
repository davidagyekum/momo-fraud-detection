import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { AuthSessionManager } from "@/lib/auth-session";
import type { User } from "@/types/api";

type AuthStatus = "restoring" | "authenticated" | "signed-out";
type AuthContextValue = {
  status: AuthStatus;
  user: User | null;
  restoreError: string | null;
  login: (input: { email: string; password: string }) => Promise<void>;
  register: (input: {
    email: string;
    password: string;
    full_name: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  retryRestore: () => Promise<void>;
  updateUser: (user: User) => void;
  request: <T>(path: string, init?: RequestInit) => Promise<T>;
  response: (path: string, init?: RequestInit) => Promise<Response>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readableError(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please retry.";
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [manager] = useState(() => new AuthSessionManager());
  const [status, setStatus] = useState<AuthStatus>("restoring");
  const [user, setUser] = useState<User | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const retryRestore = useCallback(async () => {
    setStatus("restoring");
    setRestoreError(null);
    try {
      const restoredUser = await manager.restore();
      setUser(restoredUser);
      setStatus(restoredUser ? "authenticated" : "signed-out");
    } catch (error) {
      setUser(null);
      setRestoreError(readableError(error));
      setStatus("signed-out");
    }
  }, [manager]);

  useEffect(() => {
    let active = true;
    void manager
      .restore()
      .then((restoredUser) => {
        if (!active) return;
        setUser(restoredUser);
        setStatus(restoredUser ? "authenticated" : "signed-out");
      })
      .catch((error: unknown) => {
        if (!active) return;
        setRestoreError(readableError(error));
        setStatus("signed-out");
      });
    return () => {
      active = false;
    };
  }, [manager]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      restoreError,
      login: async (input) => {
        const nextUser = await manager.login(input);
        setUser(nextUser);
        setStatus("authenticated");
      },
      register: async (input) => {
        const nextUser = await manager.register(input);
        setUser(nextUser);
        setStatus("authenticated");
      },
      logout: async () => {
        await manager.logout();
        setUser(null);
        setStatus("signed-out");
      },
      retryRestore,
      updateUser: setUser,
      request: (path, init) => manager.authorizedRequest(path, init),
      response: (path, init) => manager.authorizedResponse(path, init),
    }),
    [manager, restoreError, retryRestore, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
