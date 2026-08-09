import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";
import { BrandMark } from "../components/brand-mark";
import { Alert } from "../components/feedback";
import { Button, FormField } from "../components/primitives";
import { ApiError, requestEnvelope } from "../lib/api";

const schema = z.object({
  email: z.email("Enter a valid work email address."),
});
type Values = z.infer<typeof schema>;

export function ForgotPasswordPage(): React.ReactNode {
  const [accepted, setAccepted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const submit = async ({ email }: Values): Promise<void> => {
    setSubmitError(null);
    try {
      await requestEnvelope<{ accepted: boolean }>(
        globalThis.fetch.bind(globalThis),
        "/auth/forgot-password",
        {
          method: "POST",
          body: JSON.stringify({ email }),
        },
      );
      setAccepted(true);
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : "The request could not be completed.",
      );
    }
  };

  return (
    <main className="auth-simple">
      <BrandMark />
      <section className="auth-simple__panel" aria-labelledby="forgot-title">
        <Link to="/login" className="back-link">
          <ArrowLeft size={18} aria-hidden="true" /> Back to sign in
        </Link>
        <h1 id="forgot-title">Reset staff password</h1>
        <p>
          Enter your work email. The public response is the same whether or not
          an account exists.
        </p>
        {accepted ? (
          <Alert tone="success" title="Request accepted">
            If the account is eligible, password-reset instructions will be
            issued through the configured secure channel.
          </Alert>
        ) : (
          <form
            onSubmit={(event) => void handleSubmit(submit)(event)}
            noValidate
          >
            {submitError ? (
              <Alert tone="danger" live>
                {submitError}
              </Alert>
            ) : null}
            <FormField
              label="Work email"
              type="email"
              autoComplete="email"
              error={errors.email?.message}
              {...register("email")}
            />
            <Button type="submit" loading={isSubmitting}>
              Request reset
            </Button>
          </form>
        )}
      </section>
    </main>
  );
}
