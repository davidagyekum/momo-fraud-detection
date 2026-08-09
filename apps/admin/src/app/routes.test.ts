import { describe, expect, it } from "vitest";
import { portalRoutes, routeForPath } from "./routes";

describe("portal route permissions", () => {
  it("gives administrators the complete required shell", () => {
    expect(
      portalRoutes
        .filter((route) => route.roles.includes("ADMIN"))
        .map((route) => route.label),
    ).toEqual([
      "Dashboard",
      "Transactions",
      "Cases",
      "Users",
      "Reference Imports",
      "Receipt Templates",
      "Fraud Rules",
      "Model Registry",
      "Reports",
      "Audit Logs",
      "System Status",
    ]);
  });

  it("reduces investigator navigation to authorised workspaces", () => {
    expect(
      portalRoutes
        .filter((route) => route.roles.includes("INVESTIGATOR"))
        .map((route) => route.label),
    ).toEqual(["Dashboard", "Transactions", "Cases", "Reports"]);
  });

  it("resolves a breadcrumb route without guessing unknown paths", () => {
    expect(routeForPath("/models")?.label).toBe("Model Registry");
    expect(routeForPath("/not-real")).toBeUndefined();
  });
});
