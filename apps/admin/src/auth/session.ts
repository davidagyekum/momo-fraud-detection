import {
  ApiError,
  requestEnvelope,
  requestPrivateFile,
  savePrivateFile,
  type Fetcher,
} from "../lib/api";
import { readCookie } from "../lib/cookies";
import type { ApiEnvelope, PortalUser, SessionData } from "../types/api";

export type SessionPhase =
  "restoring" | "anonymous" | "authenticated" | "expired";

export interface SessionSnapshot {
  phase: SessionPhase;
  user: PortalUser | null;
  message: string | null;
}

type Listener = () => void;
type CookieReader = () => string;

const initialSnapshot: SessionSnapshot = {
  phase: "restoring",
  user: null,
  message: null,
};

export class PortalSession {
  private accessToken: string | null = null;
  private snapshot: SessionSnapshot = initialSnapshot;
  private listeners = new Set<Listener>();
  private refreshPromise: Promise<SessionData> | null = null;

  constructor(
    private readonly fetcher: Fetcher = globalThis.fetch.bind(globalThis),
    private readonly cookieReader: CookieReader = () => document.cookie,
  ) {}

  getSnapshot = (): SessionSnapshot => this.snapshot;

  subscribe = (listener: Listener): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  private publish(snapshot: SessionSnapshot): void {
    this.snapshot = snapshot;
    for (const listener of this.listeners) listener();
  }

  private acceptSession(data: SessionData): SessionData {
    this.accessToken = data.access_token;
    this.publish({ phase: "authenticated", user: data.user, message: null });
    return data;
  }

  private csrfToken(): string | null {
    return readCookie("momo_fdvs_csrf", this.cookieReader());
  }

  private async rotate(): Promise<SessionData> {
    if (this.refreshPromise) return this.refreshPromise;
    const csrfToken = this.csrfToken();
    if (!csrfToken) {
      throw new ApiError({
        status: 401,
        code: "SESSION_MISSING",
        message: "Your staff session is not available.",
      });
    }

    this.refreshPromise = requestEnvelope<SessionData>(
      this.fetcher,
      "/auth/refresh",
      {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken },
        body: JSON.stringify({}),
      },
    )
      .then((response) => this.acceptSession(response.data))
      .finally(() => {
        this.refreshPromise = null;
      });
    return this.refreshPromise;
  }

  async restore(): Promise<void> {
    this.publish({ phase: "restoring", user: null, message: null });
    try {
      await this.rotate();
    } catch {
      this.accessToken = null;
      this.publish({ phase: "anonymous", user: null, message: null });
    }
  }

  async signIn(email: string, password: string): Promise<PortalUser> {
    const response = await requestEnvelope<SessionData>(
      this.fetcher,
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
    );
    return this.acceptSession(response.data).user;
  }

  async signOut(): Promise<void> {
    const csrfToken = this.csrfToken();
    try {
      await requestEnvelope<{ accepted: boolean }>(
        this.fetcher,
        "/auth/logout",
        {
          method: "POST",
          headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
          body: JSON.stringify({}),
        },
        this.accessToken,
      );
    } finally {
      this.accessToken = null;
      this.publish({ phase: "anonymous", user: null, message: null });
    }
  }

  async request<T>(
    path: string,
    init: RequestInit = {},
  ): Promise<ApiEnvelope<T>> {
    if (!this.accessToken) {
      await this.rotate().catch((error: unknown) => {
        this.expire();
        throw error;
      });
    }
    try {
      return await requestEnvelope<T>(
        this.fetcher,
        path,
        init,
        this.accessToken,
      );
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      try {
        await this.rotate();
      } catch (refreshError) {
        this.expire();
        throw refreshError;
      }
      return requestEnvelope<T>(this.fetcher, path, init, this.accessToken);
    }
  }

  private expire(): void {
    this.accessToken = null;
    this.publish({
      phase: "expired",
      user: null,
      message: "Your session expired. Sign in again to continue.",
    });
  }

  accessTokenForDownload(): string {
    if (!this.accessToken) {
      throw new ApiError({
        status: 401,
        code: "SESSION_MISSING",
        message: "Sign in before downloading private evidence.",
      });
    }
    return this.accessToken;
  }

  async download(path: string, suggestedName: string): Promise<void> {
    if (!this.accessToken) await this.rotate();
    let blob: Blob;
    try {
      blob = await requestPrivateFile(
        this.fetcher,
        path,
        this.accessTokenForDownload(),
      );
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      try {
        await this.rotate();
      } catch (refreshError) {
        this.expire();
        throw refreshError;
      }
      blob = await requestPrivateFile(
        this.fetcher,
        path,
        this.accessTokenForDownload(),
      );
    }
    savePrivateFile(blob, suggestedName);
  }
}
