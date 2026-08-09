import { Eye, EyeOff, LoaderCircle } from "lucide-react";
import {
  forwardRef,
  useId,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type PropsWithChildren,
  type ReactNode,
} from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  icon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      children,
      className = "",
      variant = "primary",
      loading = false,
      icon,
      disabled,
      ...props
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        className={`button button--${variant} ${className}`.trim()}
        disabled={disabled || loading}
        aria-busy={loading}
        {...props}
      >
        <span className="button__icon" aria-hidden="true">
          {loading ? <LoaderCircle className="spin" size={18} /> : icon}
        </span>
        <span>{loading ? "Please wait…" : children}</span>
      </button>
    );
  },
);

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string | undefined;
  hint?: string | undefined;
}

export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  function FormField(
    { label, error, hint, id: suppliedId, className = "", ...props },
    ref,
  ) {
    const generatedId = useId();
    const id = suppliedId ?? generatedId;
    const descriptionId = `${id}-description`;
    return (
      <div className={`form-field ${className}`.trim()}>
        <label htmlFor={id}>{label}</label>
        <input
          ref={ref}
          id={id}
          aria-invalid={Boolean(error)}
          aria-describedby={error || hint ? descriptionId : undefined}
          {...props}
        />
        {error || hint ? (
          <p
            id={descriptionId}
            className={error ? "form-field__error" : "form-field__hint"}
          >
            {error ?? hint}
          </p>
        ) : null}
      </div>
    );
  },
);

export const PasswordField = forwardRef<HTMLInputElement, FormFieldProps>(
  function PasswordField(
    { label, error, hint, id: suppliedId, ...props },
    ref,
  ) {
    const generatedId = useId();
    const id = suppliedId ?? generatedId;
    const [visible, setVisible] = useState(false);
    const descriptionId = `${id}-description`;
    return (
      <div className="form-field">
        <label htmlFor={id}>{label}</label>
        <div className="password-field">
          <input
            ref={ref}
            id={id}
            type={visible ? "text" : "password"}
            aria-invalid={Boolean(error)}
            aria-describedby={error || hint ? descriptionId : undefined}
            {...props}
          />
          <button
            type="button"
            className="password-field__toggle"
            onClick={() => setVisible((current) => !current)}
            aria-label={visible ? "Hide password" : "Show password"}
            aria-pressed={visible}
          >
            {visible ? <EyeOff size={20} /> : <Eye size={20} />}
          </button>
        </div>
        {error || hint ? (
          <p
            id={descriptionId}
            className={error ? "form-field__error" : "form-field__hint"}
          >
            {error ?? hint}
          </p>
        ) : null}
      </div>
    );
  },
);

export function Surface({
  children,
  className = "",
}: PropsWithChildren<{ className?: string }>) {
  return (
    <section className={`surface ${className}`.trim()}>{children}</section>
  );
}
