import { expect, test, type Page } from "@playwright/test";

type StaffRole = "ADMIN" | "INVESTIGATOR";

const envelope = <T>(data: T): { data: T; meta: { request_id: string } } => ({
  data,
  meta: { request_id: "p05-playwright-smoke" },
});

function sessionFor(role: StaffRole) {
  return {
    access_token: `controlled-${role.toLowerCase()}-access-token`,
    refresh_token: null,
    csrf_token: null,
    expires_in: 900,
    user: {
      id: `controlled-${role.toLowerCase()}-id`,
      full_name:
        role === "ADMIN" ? "Controlled Admin" : "Controlled Investigator",
      email: `${role.toLowerCase()}@example.test`,
      roles: [role],
      status: "ACTIVE",
      must_change_password: false,
    },
  };
}

async function installStaffSession(page: Page, role: StaffRole): Promise<void> {
  const session = sessionFor(role);
  await page.context().addCookies([
    {
      name: "momo_fdvs_csrf",
      value: "controlled-csrf-token",
      url: "http://127.0.0.1:5174",
      sameSite: "Lax",
    },
  ]);
  await page.route("**/api/v1/auth/refresh", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(envelope(session)),
    });
  });
}

test("staff login is semantic and does not advertise public registration", async ({
  page,
}) => {
  await page.goto("/login");

  await expect(
    page.getByRole("heading", { name: "Staff sign in" }),
  ).toBeVisible();
  await expect(page.getByLabel("Work email")).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: /register|create account/i }),
  ).toHaveCount(0);
});

test("administrator shell restores securely and responds at desktop and tablet widths", async ({
  page,
}) => {
  await installStaffSession(page, "ADMIN");
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dashboard");

  await expect(
    page.getByRole("heading", { name: "Operations overview" }),
  ).toBeVisible();
  const navigation = page.getByRole("navigation", { name: "Staff portal" });
  await expect(navigation.getByRole("link")).toHaveCount(11);
  await expect(page.getByText("Fraud risk", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Verification status", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Case status", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Processing state", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);

  await page.setViewportSize({ width: 768, height: 1024 });
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.getByRole("dialog", { name: "Navigation" })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("investigator cannot reach administrator-only routes", async ({
  page,
}) => {
  await installStaffSession(page, "INVESTIGATOR");
  await page.goto("/users");

  await expect(
    page.getByRole("heading", {
      name: "You do not have access to this staff area",
    }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/no-access$/);
});
