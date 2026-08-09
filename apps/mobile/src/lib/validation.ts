import { z } from "zod";

const password = z
  .string()
  .min(12, "Use at least 12 characters.")
  .max(256, "Password is too long.");

export const loginSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});

export const registerSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your full name.").max(150),
  email: z.email("Enter a valid email address."),
  password,
});

export const forgotPasswordSchema = z.object({
  email: z.email("Enter a valid email address."),
});
export const resetPasswordSchema = z.object({
  token: z.string().min(1, "Paste the reset token from your email."),
  new_password: password,
});

export const profileSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your full name.").max(150),
  phone_e164: z
    .string()
    .trim()
    .regex(
      /^\+[1-9]\d{7,14}$/,
      "Use international format, for example +233241234567.",
    )
    .or(z.literal("")),
});
