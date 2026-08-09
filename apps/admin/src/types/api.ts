export type Role = "USER" | "ADMIN" | "INVESTIGATOR";

export interface PortalUser {
  id: string;
  full_name: string;
  email: string;
  phone_e164?: string | null;
  roles: Role[];
  status: string;
  must_change_password?: boolean;
}

export interface SessionData {
  access_token: string;
  refresh_token: null;
  csrf_token: null;
  expires_in: number;
  user: PortalUser;
}

export interface ApiEnvelope<T> {
  data: T;
  meta: {
    request_id: string;
  };
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, string[]>;
  };
  meta?: {
    request_id?: string;
  };
}
