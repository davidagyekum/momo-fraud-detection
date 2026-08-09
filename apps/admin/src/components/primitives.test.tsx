import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Button, FormField, PasswordField } from "./primitives";

describe("form primitives", () => {
  it("associates field errors with their input", () => {
    render(<FormField label="Work email" error="Enter a valid email." />);
    const input = screen.getByRole("textbox", { name: "Work email" });
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Enter a valid email.");
  });

  it("toggles password visibility with an accessible pressed state", async () => {
    const user = userEvent.setup();
    render(<PasswordField label="Password" defaultValue="secret" />);
    const input = screen.getByLabelText("Password");
    const toggle = screen.getByRole("button", { name: "Show password" });
    expect(input).toHaveAttribute("type", "password");
    await user.click(toggle);
    expect(input).toHaveAttribute("type", "text");
    expect(
      screen.getByRole("button", { name: "Hide password" }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("announces a loading button and prevents duplicate activation", () => {
    render(<Button loading>Sign in</Button>);
    const button = screen.getByRole("button", { name: "Please wait…" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });
});
