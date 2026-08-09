import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { LoginPage } from "./login-page";

const authValue: AuthContextValue = {
  phase: "anonymous",
  user: null,
  message: null,
  signIn: vi.fn(),
  signOut: vi.fn(),
  request: vi.fn(),
  accessTokenForDownload: vi.fn(),
  download: vi.fn(),
};

describe("LoginPage", () => {
  it("has no public registration and announces form errors", async () => {
    const user = userEvent.setup();
    render(
      <AuthContext.Provider value={authValue}>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </AuthContext.Provider>,
    );
    expect(
      screen.queryByText(/register|create account/i),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByText("Enter a valid work email address."),
    ).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
  });
});
