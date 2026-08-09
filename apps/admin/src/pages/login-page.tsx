import { zodResolver } from "@hookform/resolvers/zod";
import { LockKeyhole, ServerCog } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { useAuth } from "../auth/use-auth";
import { BrandMark } from "../components/brand-mark";
import { Alert } from "../components/feedback";
import { Button, FormField, PasswordField } from "../components/primitives";
import { ApiError } from "../lib/api";
import { appConfig } from "../lib/config";

const loginSchema = z.object({
  email: z.email("Enter a valid work email address."),
  password: z
    .string()
    .min(1, "Enter your password.")
    .max(256, "Password is too long."),
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginPage(): React.ReactNode {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [submitError, setSubmitError] = useState<string | null>(
    auth.phase === "expired" ? auth.message : null,
  );
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  const submit = async (values: LoginValues): Promise<void> => {
    setSubmitError(null);
    try {
      const user = await auth.signIn(values.email, values.password);
      const staff =
        user.roles.includes("ADMIN") || user.roles.includes("INVESTIGATOR");
      const requested = (location.state as { from?: string } | null)?.from;
      void navigate(staff ? requested || "/dashboard" : "/no-access", {
        replace: true,
      });
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : "Sign in could not be completed. Check your connection and try again.",
      );
    }
  };

  return (
    <main className="login-layout">
      <section className="login-story" aria-labelledby="login-story-title">
        <BrandMark />
        <div>
          <h1 id="login-story-title">
            Review evidence. Protect every decision.
          </h1>
          <span className="login-story__rule" aria-hidden="true" />
          <p>
            Fraud risk and transaction verification remain separate throughout
            every case.
          </p>
        </div>
        <div className="receipt-lines" aria-hidden="true" />
      </section>
      <section className="login-panel" aria-labelledby="staff-sign-in-title">
        <form onSubmit={(event) => void handleSubmit(submit)(event)} noValidate>
          <h2 id="staff-sign-in-title">Staff sign in</h2>
          <p>Secure access for authorised administrators and investigators.</p>
          {submitError ? (
            <Alert tone="danger" live>
              {submitError}
            </Alert>
          ) : null}
          <FormField
            label="Work email"
            type="email"
            autoComplete="username"
            placeholder="name@organisation.test"
            error={errors.email?.message}
            {...register("email")}
          />
          <PasswordField
            label="Password"
            autoComplete="current-password"
            placeholder="Enter your password"
            error={errors.password?.message}
            {...register("password")}
          />
          <Button
            className="login-panel__submit"
            type="submit"
            loading={isSubmitting}
          >
            Sign in
          </Button>
          <Link className="login-panel__forgot" to="/forgot-password">
            Forgot password?
          </Link>
          <div className="login-panel__meta">
            <p>
              <ServerCog size={20} aria-hidden="true" />
              <span>
                <strong>Environment:</strong> {appConfig.environment}
              </span>
            </p>
            <p>
              <LockKeyhole size={20} aria-hidden="true" />
              <span>Access is monitored and audited.</span>
            </p>
          </div>
        </form>
      </section>
    </main>
  );
}
