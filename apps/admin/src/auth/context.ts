import { createContext } from "react";
import type { ApiEnvelope, PortalUser } from "../types/api";
import type { SessionSnapshot } from "./session";

export interface AuthContextValue extends SessionSnapshot {
  signIn: (email: string, password: string) => Promise<PortalUser>;
  signOut: () => Promise<void>;
  request: <T>(path: string, init?: RequestInit) => Promise<ApiEnvelope<T>>;
  accessTokenForDownload: () => string;
  download: (path: string, suggestedName: string) => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
