export type User = {
  id: string;
  email: string;
  full_name: string;
  phone_e164: string | null;
  roles: string[];
  status: string;
  must_change_password: boolean;
};

export type SessionData = {
  access_token: string;
  refresh_token: string | null;
  csrf_token: string | null;
  expires_in: number;
  user: User;
};

export type Envelope<T> = { data: T; meta: Record<string, unknown> };

export type ErrorEnvelope = {
  error?: {
    code?: string;
    message?: string;
    field_errors?: Record<string, string[]>;
    details?: Record<string, unknown>;
  };
  message?: string;
};
