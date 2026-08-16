import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { DashboardPage } from "./dashboard-page";

const dashboard = {
  risk_counts: { inconclusive: 2 },
  verification_counts: { VERIFIED: 1, MISMATCH: 1 },
  case_status_counts: { OPEN: 1 },
  case_source_counts: { USER_REPORT: 1 },
  analysis_status_counts: { PARTIAL: 2 },
  processing_duration_ms: { average: 1200, p95: 1700 },
  active_versions: { models: [], rule_set: "demo-1" },
  recent_activity: [
    {
      id: "audit-1",
      action: "case_opened",
      outcome: "SUCCESS",
      target_type: "fraud_case",
      created_at: "2026-08-15T12:00:00Z",
    },
  ],
};

describe("DashboardPage", () => {
  it("renders real independent aggregates and refreshes them", async () => {
    const user = userEvent.setup();
    const request = vi.fn(() =>
      Promise.resolve({
        data: dashboard,
        meta: { request_id: "request-test" },
      }),
    ) as unknown as AuthContextValue["request"];
    const authValue: AuthContextValue = {
      phase: "authenticated",
      user: {
        id: "admin-id",
        full_name: "Ada Admin",
        email: "ada@example.test",
        roles: ["ADMIN"],
        status: "ACTIVE",
      },
      message: null,
      signIn: vi.fn(),
      signOut: vi.fn(),
      request,
      accessTokenForDownload: vi.fn(),
      download: vi.fn(),
    };
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthContext.Provider value={authValue}>
          <DashboardPage />
        </AuthContext.Provider>
      </QueryClientProvider>,
    );
    for (const label of [
      "Fraud risk",
      "Verification status",
      "Case status",
      "Processing state",
    ]) {
      expect(await screen.findByText(label)).toBeInTheDocument();
    }
    expect(screen.getAllByText("case opened").length).toBeGreaterThan(0);
    expect(
      screen.queryByText(/later phases|unavailable in P05/i),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    expect(request).toHaveBeenCalledTimes(2);
  });
});
