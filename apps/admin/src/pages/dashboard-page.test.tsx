import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { DashboardPage } from "./dashboard-page";

describe("DashboardPage", () => {
  it("keeps all four operational concepts separate and inactive", async () => {
    const user = userEvent.setup();
    render(<DashboardPage />);
    for (const label of [
      "Fraud risk",
      "Verification status",
      "Case status",
      "Processing state",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(
      screen.getByText("Operational data becomes available in later phases."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    expect(screen.getByText(/Shell state refreshed/)).toBeInTheDocument();
  });
});
