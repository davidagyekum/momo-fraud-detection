import {
  forgotPasswordSchema,
  loginSchema,
  profileSchema,
  registerSchema,
  resetPasswordSchema,
} from "@/lib/validation";

describe("mobile form validation", () => {
  test("accepts a valid registration", () => {
    expect(
      registerSchema.safeParse({
        full_name: "Ama Mensah",
        email: "ama@example.test",
        password: "fixture-valid-password",
      }).success,
    ).toBe(true);
  });

  test.each([
    [loginSchema, { email: "not-an-email", password: "" }],
    [
      registerSchema,
      { full_name: "A", email: "ama@example.test", password: "short" },
    ],
    [forgotPasswordSchema, { email: "invalid" }],
    [resetPasswordSchema, { token: "", new_password: "short" }],
    [profileSchema, { full_name: "Ama", phone_e164: "0241234567" }],
  ])("rejects invalid input", (schema, value) => {
    expect(schema.safeParse(value).success).toBe(false);
  });

  test("allows an empty optional profile phone", () => {
    expect(
      profileSchema.safeParse({ full_name: "Ama Mensah", phone_e164: "" })
        .success,
    ).toBe(true);
  });
});
