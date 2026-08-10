import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./app-shell";
import { PermissionGuard, PublicOnly, SessionGate } from "./guards";
import { portalRoutes, profileRoute } from "./routes";
import { DashboardPage } from "../pages/dashboard-page";
import { FeatureShellPage } from "../pages/feature-shell-page";
import { ForgotPasswordPage } from "../pages/forgot-password-page";
import { LoginPage } from "../pages/login-page";
import { ProfilePage } from "../pages/profile-page";
import { ReferenceImportsPage } from "../pages/reference-imports-page";
import { NoAccessPage, NotFoundPage } from "../pages/system-pages";

export function AppRouter(): React.ReactNode {
  return (
    <Routes>
      <Route element={<PublicOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      </Route>
      <Route path="/no-access" element={<NoAccessPage />} />
      <Route element={<SessionGate />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          {portalRoutes.map((route) => (
            <Route
              key={route.path}
              path={route.path}
              element={
                <PermissionGuard roles={route.roles}>
                  {route.path === "/dashboard" ? (
                    <DashboardPage />
                  ) : route.path === "/reference-imports" ? (
                    <ReferenceImportsPage />
                  ) : (
                    <FeatureShellPage route={route} />
                  )}
                </PermissionGuard>
              }
            />
          ))}
          <Route
            path={profileRoute.path}
            element={
              <PermissionGuard roles={profileRoute.roles}>
                <ProfilePage />
              </PermissionGuard>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
