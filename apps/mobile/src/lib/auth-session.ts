import { apiRequest, ApiError } from "@/lib/api";
import {
  clearRefreshToken,
  readRefreshToken,
  writeRefreshToken,
} from "@/lib/token-vault";
import type { Envelope, SessionData, User } from "@/types/api";

type Credentials = { email: string; password: string };
type Registration = Credentials & { full_name: string };

export class AuthSessionManager {
  private accessToken: string | null = null;
  private refreshInFlight: Promise<User | null> | null = null;

  private async acceptSession(session: SessionData): Promise<User> {
    if (!session.refresh_token) {
      throw new ApiError(
        "The API returned a partial mobile session. Sign in again later.",
        503,
        "PARTIAL_SESSION",
      );
    }
    this.accessToken = session.access_token;
    await writeRefreshToken(session.refresh_token);
    return session.user;
  }

  async login(credentials: Credentials): Promise<User> {
    const response = await apiRequest<Envelope<SessionData>>(
      "/api/v1/auth/login",
      {
        method: "POST",
        body: JSON.stringify(credentials),
      },
    );
    return this.acceptSession(response.data);
  }

  async register(input: Registration): Promise<User> {
    const response = await apiRequest<Envelope<SessionData>>(
      "/api/v1/auth/register",
      {
        method: "POST",
        body: JSON.stringify(input),
      },
    );
    return this.acceptSession(response.data);
  }

  async restore(): Promise<User | null> {
    if (this.refreshInFlight) return this.refreshInFlight;
    this.refreshInFlight = this.performRefresh().finally(() => {
      this.refreshInFlight = null;
    });
    return this.refreshInFlight;
  }

  private async performRefresh(): Promise<User | null> {
    const refreshToken = await readRefreshToken();
    if (!refreshToken) return null;
    try {
      const response = await apiRequest<Envelope<SessionData>>(
        "/api/v1/auth/refresh",
        {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        },
      );
      return await this.acceptSession(response.data);
    } catch (error) {
      if (error instanceof ApiError && [401, 403].includes(error.status)) {
        await this.clearLocalSession();
      }
      throw error;
    }
  }

  async authorizedRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
    if (!this.accessToken) await this.restore();
    try {
      return await apiRequest<T>(path, init, this.accessToken ?? undefined);
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
      const user = await this.restore();
      if (!user || !this.accessToken) throw error;
      return apiRequest<T>(path, init, this.accessToken);
    }
  }

  async logout(): Promise<void> {
    const refreshToken = await readRefreshToken();
    try {
      if (refreshToken) {
        await apiRequest("/api/v1/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      }
    } finally {
      await this.clearLocalSession();
    }
  }

  async clearLocalSession(): Promise<void> {
    this.accessToken = null;
    await clearRefreshToken();
  }
}
